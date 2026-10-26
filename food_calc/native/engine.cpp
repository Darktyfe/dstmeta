// engine.cpp - DSTMeta crockpot plan search in C++.
//
// This is a faithful port of the Python engine in food_calc/code/alg.py:
//   _pareto()             -> pareto()
//   _individual_frontier()-> individual_frontier()
//   _solve_frontier()     -> solve()
//   find_best_plan()      -> dstmeta_solve()
// Same iteration order, tie-breaking and floating point operations, so both
// engines agree on totals and plans.
//
// Data is passed in with plain arrays (see food_calc/code/cpp_engine.py for
// the Python side).  Individual and pot options are the actual stat vectors
// (negative allowed); feasibility and ranking are applied here.
//
// All search state is local to one call, so concurrent calls are safe.

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <deque>
#include <string>
#include <unordered_map>
#include <vector>

#if defined(_WIN32)
#define EXPORT extern "C" __declspec(dllexport)
#else
#define EXPORT extern "C" __attribute__((visibility("default")))
#endif

namespace {

constexpr double kEps = 1e-9;
constexpr uint8_t kCookKind = 4;
constexpr int32_t kMaxTypes = 48;
constexpr int32_t kMaxPerType = 255;
constexpr int64_t kMaxInstances = 1024;

using Vec = std::array<double, 3>;

// Action kinds: 0 keep, 1 eat, 2 roast, 3 dry, 4 cook.  Individual kinds are
// handed in by cpp_engine.ACTION_KINDS; the cook kind is fixed here.
struct Act {
    uint8_t kind;
    uint8_t type;       // item type for individual actions
    uint8_t g[4];       // sorted type multiset for cook actions
    uint16_t dish;      // dish id for cook actions
    uint16_t cooked;    // cooked ingredient count for cook actions
};

struct Node;
using NodeRef = const Node*;   // non-owning, points into an arena

// Persistent (share-everything-but-the-head) action list, newest first.
struct Node {
    Act act;
    NodeRef prev;
    int32_t len;
    int32_t pot_cooked;
};

struct Point {
    Vec v;
    NodeRef tail;
    int32_t len;
    int32_t pot_cooked;
};

using Points = std::vector<Point>;

inline std::array<double, 3> add(const Vec& a, const double* b) {
    return {a[0] + b[0], a[1] + b[1], a[2] + b[2]};
}

// a >= b in every stat (ties allowed)
inline bool ge_all(const double* a, const double* b) {
    return a[0] >= b[0] - kEps && a[1] >= b[1] - kEps && a[2] >= b[2] - kEps;
}

// strictly better in at least one stat
inline bool gt_any(const double* a, const double* b) {
    return a[0] > b[0] + kEps || a[1] > b[1] + kEps || a[2] > b[2] + kEps;
}

inline bool dominates(const Point& a, const Point& b) {
    return ge_all(a.v.data(), b.v.data()) && gt_any(a.v.data(), b.v.data());
}

using VecKey = std::array<int32_t, 3>;

struct VecKeyHash {
    size_t operator()(const VecKey& key) const noexcept {
        uint64_t h = 1469598103934665603ull;
        for (int32_t part : key) {
            h ^= static_cast<uint32_t>(part);
            h *= 1099511628211ull;
        }
        return static_cast<size_t>(h);
    }
};

// Same rounding as Python's round(value, 6) for our data range.
VecKey round_key(const Vec& v) {
    return VecKey{
        static_cast<int32_t>(std::llrint(v[0] * 1e6)),
        static_cast<int32_t>(std::llrint(v[1] * 1e6)),
        static_cast<int32_t>(std::llrint(v[2] * 1e6)),
    };
}

struct Task {
    int32_t types = 0;
    std::vector<int32_t> counts;
    std::vector<int32_t> ind_off;          // types + 1
    const double* ind_stats = nullptr;     // 3 per individual option
    const int32_t* ind_kind = nullptr;     // 1 per individual option
    int32_t pot_count = 0;
    std::unordered_map<uint32_t, std::pair<int32_t, int32_t>> pot_index;
    const int32_t* pot_dish = nullptr;
    const double* pot_stats = nullptr;     // 3 per pot option
    const int8_t* pot_cooked = nullptr;
    int32_t chosen = 0;
    Vec losses{};

    // Single allocation arena for every action list of this call.  Nodes
    // never move (deque never invalidates references) and are freed together,
    // which is far cheaper than one heap allocation per point.
    std::deque<Node> nodes;

    Point empty_point{};                     // the all-keep no-action plan
    std::vector<Point> empty_ind;            // frontier for an empty inventory
    std::unordered_map<std::string, Points> ind_memo;
    std::unordered_map<std::string, Points> solve_memo;
};

inline NodeRef push_node(Task& task, const Point& point, const Act& act) {
    task.nodes.push_back(
        Node{act, point.tail, point.len + 1,
             point.pot_cooked + (act.kind == kCookKind ? act.cooked : 0)});
    return &task.nodes.back();
}

// Mirrors alg._pareto: collapse identical vectors keeping the best
// (pot_cooked, steps) key, then drop dominated points in insertion order.
Points pareto(Points input) {
    std::unordered_map<VecKey, size_t, VecKeyHash> index;
    std::vector<Point> unique;
    unique.reserve(input.size());
    for (Point& point : input) {
        const VecKey key = round_key(point.v);
        auto found = index.find(key);
        if (found == index.end()) {
            index.emplace(key, unique.size());
            unique.push_back(std::move(point));
            continue;
        }
        Point& kept = unique[found->second];
        if (point.pot_cooked < kept.pot_cooked ||
            (point.pot_cooked == kept.pot_cooked && point.len < kept.len)) {
            kept = std::move(point);
        }
    }
    index.clear();

    Points kept;
    kept.reserve(unique.size());
    for (Point& point : unique) {
        bool dominated = false;
        for (const Point& other : kept) {
            if (dominates(other, point)) {
                dominated = true;
                break;
            }
        }
        if (dominated) {
            continue;
        }
        kept.erase(
            std::remove_if(kept.begin(), kept.end(),
                [&point](const Point& other) { return dominates(point, other); }),
            kept.end());
        kept.push_back(std::move(point));
    }
    return kept;
}

std::string counts_key(const Task& task, const int32_t* counts) {
    return std::string(reinterpret_cast<const char*>(counts),
                       static_cast<size_t>(task.types) * sizeof(int32_t));
}

bool has_items(const int32_t* counts, int32_t types, int32_t* first) {
    for (int32_t t = 0; t < types; ++t) {
        if (counts[t] > 0) {
            *first = t;
            return true;
        }
    }
    return false;
}

const Points& individual_frontier(Task& task, const int32_t* counts);

// Mirrors alg._individual_frontier.  Returns a reference into the memo, so
// callers must copy before inserting into the same map again.
const Points& individual_frontier(Task& task, const int32_t* counts) {
    int32_t first = -1;
    if (!has_items(counts, task.types, &first)) {
        return task.empty_ind;
    }

    const std::string key = counts_key(task, counts);
    auto memo = task.ind_memo.find(key);
    if (memo != task.ind_memo.end()) {
        return memo->second;
    }

    std::vector<int32_t> child(counts, counts + task.types);
    child[first] -= 1;
    const Points& base = individual_frontier(task, child.data());

    const int32_t begin = task.ind_off[first];
    const int32_t end = task.ind_off[first + 1];

    Points merged;
    merged.reserve(base.size() * static_cast<size_t>(end > begin ? end - begin : 0));
    for (const Point& point : base) {
        for (int32_t o = begin; o < end; ++o) {
            Act act{};
            act.kind = static_cast<uint8_t>(task.ind_kind[o]);
            act.type = static_cast<uint8_t>(first);
            Point next;
            next.v = add(point.v, &task.ind_stats[o * 3]);
            next.tail = push_node(task, point, act);
            next.len = point.len + 1;
            next.pot_cooked = point.pot_cooked;
            merged.push_back(next);
        }
    }

    Points result = pareto(std::move(merged));
    return task.ind_memo.emplace(key, std::move(result)).first->second;
}

// Mirrors alg._solve_frontier.solve.  Returns a reference into the memo.
const Points& solve(Task& task, const int32_t* counts) {
    int32_t first = -1;
    if (!has_items(counts, task.types, &first)) {
        return individual_frontier(task, counts);
    }

    const std::string key = counts_key(task, counts);
    auto memo = task.solve_memo.find(key);
    if (memo != task.solve_memo.end()) {
        return memo->second;
    }

    std::vector<int32_t> remaining(counts, counts + task.types);
    remaining[first] -= 1;

    // Either the first item is used on its own (kept, eaten, roasted or
    // dried), in which case the rest of the inventory is still free to cook,
    // or it joins three other items in the pot.  Solving only the pot groups
    // would miss every plan that leaves the first item out of the pot but
    // cooks some of the remaining items.
    Points points;
    const int32_t begin = task.ind_off[first];
    const int32_t end = task.ind_off[first + 1];
    const Points& sub_rest = solve(task, remaining.data());
    points.reserve(sub_rest.size() * static_cast<size_t>(end - begin));
    for (int32_t o = begin; o < end; ++o) {
        for (const Point& point : sub_rest) {
            Act act{};
            act.kind = static_cast<uint8_t>(task.ind_kind[o]);
            act.type = static_cast<uint8_t>(first);
            Point next;
            next.v = add(point.v, &task.ind_stats[o * 3]);
            next.tail = push_node(task, point, act);
            next.len = point.len + 1;
            next.pot_cooked = point.pot_cooked;
            points.push_back(next);
        }
    }

    // Every 3-item multiset drawn from the remaining items; each type index
    // may repeat depending on its count.  Always ascending, so the group is
    // the sorted 4-tuple (first, a, b, c).
    for (int32_t a = first; a < task.types; ++a) {
        if (remaining[a] < 1) {
            continue;
        }
        remaining[a] -= 1;
        for (int32_t b = a; b < task.types; ++b) {
            if (remaining[b] < 1) {
                continue;
            }
            remaining[b] -= 1;
            for (int32_t c = b; c < task.types; ++c) {
                if (remaining[c] < 1) {
                    continue;
                }
                remaining[c] -= 1;

                const uint32_t key4 =
                    (static_cast<uint32_t>(first) << 24) |
                    (static_cast<uint32_t>(a) << 16) |
                    (static_cast<uint32_t>(b) << 8) |
                    static_cast<uint32_t>(c);
                auto found = task.pot_index.find(key4);
                if (found != task.pot_index.end()) {
                    const auto range = found->second;
                    if (range.second > 0) {
                        std::vector<int32_t> sub_counts(counts, counts + task.types);
                        sub_counts[first] -= 1;
                        sub_counts[a] -= 1;
                        sub_counts[b] -= 1;
                        sub_counts[c] -= 1;
                        const Points& sub = solve(task, sub_counts.data());

                        Act act{};
                        act.kind = kCookKind;
                        act.g[0] = static_cast<uint8_t>(first);
                        act.g[1] = static_cast<uint8_t>(a);
                        act.g[2] = static_cast<uint8_t>(b);
                        act.g[3] = static_cast<uint8_t>(c);
                        for (int32_t o = range.first; o < range.first + range.second; ++o) {
                            act.dish = static_cast<uint16_t>(task.pot_dish[o]);
                            act.cooked = static_cast<uint16_t>(task.pot_cooked[o]);
                            const double* stats = &task.pot_stats[o * 3];
                            for (const Point& point : sub) {
                                Point next;
                                next.v = add(point.v, stats);
                                next.tail = push_node(task, point, act);
                                next.len = point.len + 1;
                                next.pot_cooked = point.pot_cooked + act.cooked;
                                points.push_back(next);
                            }
                        }
                    }
                }

                remaining[c] += 1;
            }
            remaining[b] += 1;
        }
        remaining[a] += 1;
    }

    Points result = pareto(std::move(points));
    return task.solve_memo.emplace(key, std::move(result)).first->second;
}

// Same tuple ranking as alg.find_best_plan.rank (max keeps the first winner).
bool better(const Point& candidate, const Point& best, int32_t chosen) {
    if (candidate.v[chosen] != best.v[chosen]) {
        return candidate.v[chosen] > best.v[chosen];
    }
    if (candidate.v[2] != best.v[2]) {
        return candidate.v[2] > best.v[2];
    }
    if (candidate.v[1] != best.v[1]) {
        return candidate.v[1] > best.v[1];
    }
    if (candidate.pot_cooked != best.pot_cooked) {
        return candidate.pot_cooked < best.pot_cooked;
    }
    return candidate.len < best.len;
}

bool feasible(const Point& point, const Vec& losses) {
    return point.v[0] >= -losses[0] - kEps && point.v[1] >= -losses[1] - kEps &&
           point.v[2] >= -losses[2] - kEps;
}

}  // namespace

// Return codes: 0 ok, -1 bad arguments, -2 limits exceeded, -3 no plan.
EXPORT int32_t dstmeta_solve(
    int32_t types,
    const int32_t* type_counts,
    const int32_t* ind_off,
    const double* ind_stats,
    const int32_t* ind_kind,
    int32_t pot_count,
    const int32_t* pot_keys,      // pot_count * 4 sorted type indices
    const int32_t* pot_off,       // pot_count + 1
    const int32_t* pot_dish,      // option count
    const double* pot_stats,      // option count * 3
    const int8_t* pot_cooked,     // option count
    int32_t chosen_stat,
    const double* losses,         // 3
    double* out_total,
    double* out_totals,           // 3
    int32_t* out_group_count,
    int32_t* out_groups,          // groups_cap * 5 (dish_id, t0, t1, t2, t3)
    int32_t groups_cap,
    int8_t* out_ind)              // types * 4 (keep, eat, roast, dry counts)
{
    if (types <= 0 || types > kMaxTypes || type_counts == nullptr ||
        ind_off == nullptr || ind_stats == nullptr || ind_kind == nullptr ||
        chosen_stat < 0 || chosen_stat > 2 || losses == nullptr ||
        out_total == nullptr || out_totals == nullptr ||
        out_group_count == nullptr || out_groups == nullptr ||
        groups_cap < 1 || out_ind == nullptr || pot_off == nullptr ||
        (pot_count > 0 &&
         (pot_keys == nullptr || pot_dish == nullptr || pot_stats == nullptr ||
          pot_cooked == nullptr))) {
        return -1;
    }

    int64_t instances = 0;
    for (int32_t t = 0; t < types; ++t) {
        if (type_counts[t] < 0 || type_counts[t] > kMaxPerType) {
            return -2;
        }
        instances += type_counts[t];
    }
    if (instances > kMaxInstances) {
        return -2;
    }

    Task task;
    task.types = types;
    task.counts.assign(type_counts, type_counts + types);
    task.ind_off.assign(ind_off, ind_off + types + 1);
    if (task.ind_off.front() != 0 || task.ind_off.back() < task.ind_off.front()) {
        return -1;
    }
    for (int32_t t = 0; t < types; ++t) {
        if (task.ind_off[t] > task.ind_off[t + 1]) {
            return -1;
        }
    }
    task.ind_stats = ind_stats;
    task.ind_kind = ind_kind;
    task.pot_count = pot_count;
    task.pot_dish = pot_dish;
    task.pot_stats = pot_stats;
    task.pot_cooked = pot_cooked;
    task.chosen = chosen_stat;
    task.losses = {losses[0], losses[1], losses[2]};

    task.empty_ind.push_back(
        Point{Vec{0.0, 0.0, 0.0}, nullptr, 0, 0});

    for (int32_t m = 0; m < pot_count; ++m) {
        const int32_t* quad = pot_keys + m * 4;
        for (int32_t i = 0; i < 4; ++i) {
            if (quad[i] < 0 || quad[i] >= types) {
                return -1;
            }
        }
        if (!(quad[0] <= quad[1] && quad[1] <= quad[2] && quad[2] <= quad[3])) {
            return -1;
        }
        if (m + 1 < pot_count && pot_off[m] > pot_off[m + 1]) {
            return -1;
        }
        const uint32_t key = (static_cast<uint32_t>(quad[0]) << 24) |
                             (static_cast<uint32_t>(quad[1]) << 16) |
                             (static_cast<uint32_t>(quad[2]) << 8) |
                             static_cast<uint32_t>(quad[3]);
        task.pot_index[key] = {pot_off[m], pot_off[m + 1] - pot_off[m]};
    }

    const Points& result_points = solve(task, task.counts.data());

    const Point* best = nullptr;
    for (const Point& point : result_points) {
        if (!feasible(point, task.losses)) {
            continue;
        }
        if (best == nullptr || better(point, *best, task.chosen)) {
            best = &point;
        }
    }
    if (best == nullptr) {
        return -3;
    }

    *out_total = best->v[task.chosen];
    out_totals[0] = best->v[0];
    out_totals[1] = best->v[1];
    out_totals[2] = best->v[2];

    std::vector<Act> actions;
    actions.reserve(static_cast<size_t>(best->len));
    for (NodeRef node = best->tail; node != nullptr; node = node->prev) {
        actions.push_back(node->act);
    }
    std::reverse(actions.begin(), actions.end());

    int32_t groups = 0;
    for (const Act& act : actions) {
        if (act.kind != kCookKind) {
            continue;
        }
        if (groups >= groups_cap) {
            return -2;
        }
        out_groups[groups * 5 + 0] = act.dish;
        out_groups[groups * 5 + 1] = act.g[0];
        out_groups[groups * 5 + 2] = act.g[1];
        out_groups[groups * 5 + 3] = act.g[2];
        out_groups[groups * 5 + 4] = act.g[3];
        ++groups;
    }
    *out_group_count = groups;

    std::memset(out_ind, 0, static_cast<size_t>(types) * 4);
    for (const Act& act : actions) {
        if (act.kind != kCookKind) {
            out_ind[static_cast<size_t>(act.type) * 4 + act.kind] += 1;
        }
    }

    return 0;
}
