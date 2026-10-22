(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const els = {
    form: $("#planner"),
    ingredients: $("#ingredients"),
    itemCount: $("#item-count"),
    sample: $("#sample"),
    statButtons: $$(".segmented button"),
    warly: $("#warly"),
    lossHunger: $("#loss-hunger"),
    lossSanity: $("#loss-sanity"),
    lossHealth: $("#loss-health"),
    calculate: $("#calculate"),
    buttonLabel: $("#calculate .button-label"),
    error: $("#error"),
    results: $("#results"),
    summaryStat: $("#summary-stat"),
    totalValue: $("#total-value"),
    totalUnit: $("#total-unit"),
    planMeta: $("#plan-meta"),
    totalChips: $("#total-chips"),
    lossSummary: $("#loss-summary"),
    unknown: $("#unknown"),
    planSteps: $("#plan-steps"),
    bestCard: $("#best-card"),
    bestName: $("#best-name"),
    bestStats: $("#best-stats"),
    bestCombo: $("#best-combo"),
    dishesDetails: $(".dishes-card details"),
    dishesCount: $("#dishes-count"),
    dishesNote: $("#dishes-note"),
    dishesGrid: $("#dishes-grid"),
  };

  const state = {
    stat: "Hunger",
    loading: false,
  };

  const STAT_KEYS = ["Hunger", "Sanity", "Health"];
  const STAT_CLASS = { Hunger: "hunger", Sanity: "sanity", Health: "health" };
  const STEP_ICON = { cook: "🍲", roast: "🔥", eat: "🍴", keep: "✋" };
  const STEP_VERB = { cook: "Cook", roast: "Roast", eat: "Eat", keep: "Keep" };

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function fmt(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "0";
    const rounded = Math.round(number * 100) / 100;
    return String(rounded);
  }

  function countIngredients() {
    const names = els.ingredients.value
      .split(/[\n,]/)
      .map((name) => name.trim())
      .filter(Boolean);
    const label = names.length === 1 ? "1 item" : `${names.length} items`;
    els.itemCount.textContent = label;
  }

  function setStat(stat) {
    state.stat = stat;
    els.statButtons.forEach((button) => {
      const active = button.dataset.stat === stat;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function readLoss(input) {
    const value = Number(input.value);
    return Number.isFinite(value) && value > 0 ? value : 0;
  }

  function lossesPayload() {
    return {
      Hunger: readLoss(els.lossHunger),
      Sanity: readLoss(els.lossSanity),
      Health: readLoss(els.lossHealth),
    };
  }

  function showError(message) {
    els.error.textContent = message;
    els.error.hidden = false;
  }

  function clearError() {
    els.error.textContent = "";
    els.error.hidden = true;
  }

  function setLoading(loading) {
    state.loading = loading;
    els.calculate.disabled = loading;
    els.calculate.classList.toggle("loading", loading);
    els.buttonLabel.textContent = loading ? "Calculating…" : "Calculate plan";
  }

  async function calculate(event) {
    event.preventDefault();
    if (state.loading) return;
    clearError();

    const ingredients = els.ingredients.value.trim();
    if (!ingredients) {
      showError("Add at least one ingredient first.");
      els.ingredients.focus();
      return;
    }

    setLoading(true);
    const wasHidden = els.results.hidden;

    try {
      const response = await fetch("/api/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ingredients,
          stat: state.stat,
          warly: els.warly.checked,
          losses: lossesPayload(),
        }),
      });

      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error("The calculator returned an unreadable response.");
      }

      if (!response.ok) {
        throw new Error(data.error || "The calculator could not build a plan.");
      }

      render(data);
      els.results.hidden = false;
      if (wasHidden) {
        els.results.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    } catch (error) {
      showError(
        error instanceof TypeError
          ? "Could not reach the calculator. Is the local server running?"
          : error.message
      );
    } finally {
      setLoading(false);
    }
  }

  function chip(stat, value) {
    const node = el("span", `chip ${STAT_CLASS[stat]}`);
    if (Number(value) < -1e-9) node.classList.add("negative");
    node.append(document.createTextNode(stat));
    node.append(el("b", null, fmt(value)));
    return node;
  }

  function miniStat(stat, value) {
    const node = el("span", Number(value) < -1e-9 ? "mini-stat negative" : "mini-stat");
    node.append(document.createTextNode(`${stat} `));
    node.append(el("b", null, fmt(value)));
    return node;
  }

  function fillChips(container, stats) {
    clear(container);
    STAT_KEYS.forEach((stat) => {
      container.append(chip(stat, stats[stat] ?? 0));
    });
  }

  function fillCombo(container, combo) {
    clear(container);
    combo.forEach((ingredient, index) => {
      if (index) container.append(document.createTextNode(" "));
      container.append(el("span", null, ingredient));
    });
  }

  function stepTitle(action) {
    const title = el("div", "step-title");
    title.append(el("span", "verb", STEP_VERB[action.kind] || action.kind));

    if (action.kind === "cook") {
      title.append(document.createTextNode(action.ingredients.join(", ")));
      title.append(el("span", "arrow", "→"));
      title.append(document.createTextNode(action.food));
    } else if (action.kind === "roast") {
      title.append(document.createTextNode(action.source));
      title.append(el("span", "arrow", "→"));
      title.append(document.createTextNode(action.food));
    } else {
      title.append(document.createTextNode(action.food));
    }

    return title;
  }

  function stepNode(action) {
    const item = el("li", `step step-${action.kind}`);
    item.append(el("div", "step-icon", STEP_ICON[action.kind] || "•"));

    const body = el("div", "step-body");
    body.append(stepTitle(action));

    const stats = el("div", "step-stats");
    if (action.kind === "keep") {
      stats.append(el("span", "mini-stat", "not eaten"));
    } else {
      STAT_KEYS.forEach((stat) => {
        stats.append(miniStat(stat, action.stats[stat] ?? 0));
      });
    }
    body.append(stats);
    item.append(body);
    return item;
  }

  function renderPlan(data) {
    clear(els.planSteps);
    data.plan.forEach((action) => {
      els.planSteps.append(stepNode(action));
    });
  }

  function renderUnknown(names) {
    if (!names.length) {
      els.unknown.hidden = true;
      els.unknown.textContent = "";
      return;
    }
    els.unknown.hidden = false;
    els.unknown.textContent =
      `Not in the food data: ${names.join(", ")}. ` +
      "They were treated as plain ingredients.";
  }

  function renderDishes(data) {
    clear(els.dishesGrid);
    els.dishesCount.textContent = String(data.totalDishes);

    if (!data.dishes.length) {
      els.dishesNote.textContent =
        "Add at least four ingredients to see crockpot dishes.";
      return;
    }

    if (data.totalDishes > data.dishes.length) {
      els.dishesNote.textContent =
        `Showing the top ${data.dishes.length} of ${data.totalDishes} dishes for ${data.stat}.`;
    } else {
      els.dishesNote.textContent =
        `${data.totalDishes} dish${data.totalDishes === 1 ? "" : "es"} can be made, ` +
        `ranked by ${data.stat.toLowerCase()}.`;
    }

    data.dishes.forEach((dish) => {
      const card = el("article", "dish");

      const head = el("div", "dish-head");
      head.append(el("span", "dish-name", dish.name));
      head.append(
        el("span", "dish-score", `${fmt(dish.score)} ${data.stat.toLowerCase()}`)
      );

      const stats = el("div", "dish-stats");
      STAT_KEYS.forEach((stat) => {
        stats.append(el("span", null, `${stat} ${fmt(dish.stats[stat] ?? 0)}`));
      });

      const combo = el("p", "dish-combo", dish.combination.join(" + "));
      card.append(head, stats, combo);
      els.dishesGrid.append(card);
    });

    els.dishesDetails.open = data.totalDishes <= 18;
  }

  function render(data) {
    els.summaryStat.textContent = data.stat;
    els.totalValue.textContent = fmt(data.total);
    els.totalUnit.textContent = data.stat.toLowerCase();

    const steps = data.plan.length;
    const items = data.ingredients.length;
    els.planMeta.textContent =
      `${steps} step${steps === 1 ? "" : "s"} · ` +
      `${items} ingredient${items === 1 ? "" : "s"} · ` +
      (data.warly ? "Warly recipes included" : "standard recipes");

    fillChips(els.totalChips, data.totals);

    const allowed = STAT_KEYS.filter((stat) => Number(data.losses[stat]) > 0);
    if (allowed.length) {
      els.lossSummary.textContent =
        "Allowed loss: " +
        allowed.map((stat) => `${stat.toLowerCase()} ${fmt(data.losses[stat])}`).join(", ");
    } else {
      els.lossSummary.textContent = "No net losses allowed";
    }

    renderUnknown(data.unknown);
    renderPlan(data);

    if (data.bestDish) {
      els.bestCard.hidden = false;
      els.bestName.textContent = data.bestDish.name;
      fillChips(els.bestStats, data.bestDish.stats);
      fillCombo(els.bestCombo, data.bestDish.combination);
    } else {
      els.bestCard.hidden = true;
    }

    renderDishes(data);
  }

  els.ingredients.addEventListener("input", countIngredients);
  els.ingredients.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      els.form.requestSubmit();
    }
  });

  els.statButtons.forEach((button) => {
    button.addEventListener("click", () => setStat(button.dataset.stat));
  });

  [els.lossHunger, els.lossSanity, els.lossHealth].forEach((input) => {
    input.addEventListener("blur", () => {
      const value = Number(input.value);
      input.value = Number.isFinite(value) && value > 0 ? String(value) : "0";
    });
    input.addEventListener("input", clearError);
  });

  els.sample.addEventListener("click", () => {
    els.ingredients.value = "Meat\nMeat\nMeat\nIce\nMeat";
    countIngredients();
    setStat("Hunger");
    els.ingredients.focus();
  });

  els.form.addEventListener("submit", calculate);
  els.warly.addEventListener("change", clearError);
  els.ingredients.addEventListener("input", clearError);

  setStat(state.stat);
  countIngredients();
})();
