(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const I18N = window.DSTMETA_I18N || { en: {} };

  const els = {
    form: $("#planner"),
    ingredients: $("#ingredients"),
    itemCount: $("#item-count"),
    maxIngredients: $("#max-ingredients"),
    maxTypes: $("#max-types"),
    sample: $("#sample"),
    langButtons: $$(".lang-switch button"),
    statButtons: $$(".segmented button"),
    warly: $("#warly"),
    ignoreDried: $("#ignore-dried"),
    ignoreMilkmade: $("#ignore-milkmade"),
    ignoreOverTime: $("#ignore-over-time"),
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
    planSteps: $("#plan-steps"),
    planMode: $("#plan-mode"),
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
    lang: "en",
    stat: "Hunger",
    loading: false,
    data: null,
    errorKey: null,
  };

  const STAT_KEYS = ["Hunger", "Sanity", "Health"];
  const STAT_CLASS = { Hunger: "hunger", Sanity: "sanity", Health: "health" };
  const STEP_ICON = {
    cook: "🍲", roast: "🔥", dry: "🥓", eat: "🍴", keep: "✋", prep: "🔪",
  };
  const STEP_VERB_KEY = {
    cook: "verbCook",
    roast: "verbRoast",
    dry: "verbDry",
    eat: "verbEat",
    keep: "verbKeep",
    prep: "verbPrep",
  };

  let ruNames = null;

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

  function t(key, vars) {
    const dict = I18N[state.lang] || {};
    let text = dict[key];
    if (text === undefined) text = (I18N.en || {})[key];
    if (text === undefined) return key;
    if (vars) {
      Object.keys(vars).forEach((name) => {
        text = text.split(`{${name}}`).join(String(vars[name]));
      });
    }
    return text;
  }

  function pluralForm(n) {
    if (state.lang !== "ru") return n === 1 ? "One" : "Many";
    const mod100 = Math.abs(n) % 100;
    const mod10 = mod100 % 10;
    if (mod100 > 10 && mod100 < 20) return "Many";
    if (mod10 === 1) return "One";
    if (mod10 >= 2 && mod10 <= 4) return "Few";
    return "Many";
  }

  function countWord(n, base) {
    return t(base + pluralForm(n));
  }

  function statName(stat) {
    return t(`stat${stat}`);
  }

  function statUnit(stat) {
    return t(`statUnit${stat}`);
  }

  function statBy(stat) {
    return t(`statBy${stat}`);
  }

  function foodName(name) {
    if (state.lang === "ru" && ruNames && ruNames[name]) return ruNames[name];
    return name;
  }

  function storedLang() {
    try {
      const saved = localStorage.getItem("dstmeta.lang");
      return saved === "en" || saved === "ru" ? saved : null;
    } catch (error) {
      return null;
    }
  }

  function detectLang() {
    const saved = storedLang();
    if (saved) return saved;
    const browser = (navigator.language || "en").toLowerCase();
    return browser.startsWith("ru") ? "ru" : "en";
  }

  async function loadRuNames() {
    if (ruNames) return ruNames;
    try {
      const response = await fetch("names_ru.json", { cache: "no-store" });
      if (response.ok) ruNames = await response.json();
    } catch (error) {
      // Fall back to the canonical English names.
    }
    if (!ruNames) ruNames = {};
    return ruNames;
  }

  function countIngredients() {
    const names = els.ingredients.value
      .split(/[\n,]/)
      .map((name) => name.trim())
      .filter(Boolean);
    els.itemCount.textContent =
      `${names.length} ${countWord(names.length, "item")}`;
  }

  function applyLanguage(lang) {
    state.lang = lang === "ru" ? "ru" : "en";
    try {
      localStorage.setItem("dstmeta.lang", state.lang);
    } catch (error) {
      // Storage may be unavailable; the switch still works for this page.
    }

    document.documentElement.lang = state.lang;
    document.title = t("title");
    const description = document.querySelector('meta[name="description"]');
    if (description) description.setAttribute("content", t("metaDescription"));

    $$("[data-i18n]").forEach((node) => {
      node.textContent = t(node.dataset.i18n);
    });
    $$("[data-i18n-placeholder]").forEach((node) => {
      node.placeholder = t(node.dataset.i18nPlaceholder);
    });
    $$("[data-i18n-aria-label]").forEach((node) => {
      node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel));
    });

    els.langButtons.forEach((button) => {
      const active = button.dataset.lang === state.lang;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });

    countIngredients();
    setLoading(state.loading);
    if (state.errorKey) showError(t(state.errorKey), state.errorKey);
    if (state.data) render(state.data);
  }

  async function switchLanguage(lang) {
    if (lang === state.lang) return;
    if (!state.errorKey) clearError();
    if (lang === "ru") {
      await loadRuNames();
    }
    applyLanguage(lang);
  }

  async function loadServerConfig() {
    try {
      const response = await fetch("/api/foods");
      if (!response.ok) return;
      const data = await response.json();
      if (Number.isFinite(data.maxIngredients)) {
        els.maxIngredients.textContent = String(data.maxIngredients);
      }
      if (Number.isFinite(data.maxIngredientTypes)) {
        els.maxTypes.textContent = String(data.maxIngredientTypes);
      }
    } catch (error) {
      // Keep the static fallback from index.html.
    }
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

  function showError(message, key) {
    state.errorKey = key || null;
    els.error.textContent = message;
    els.error.hidden = false;
  }

  function clearError() {
    state.errorKey = null;
    els.error.textContent = "";
    els.error.hidden = true;
  }

  function setLoading(loading) {
    state.loading = loading;
    els.calculate.disabled = loading;
    els.calculate.classList.toggle("loading", loading);
    els.buttonLabel.textContent = loading ? t("calculating") : t("calculate");
  }

  async function calculate(event) {
    event.preventDefault();
    if (state.loading) return;
    clearError();

    const ingredients = els.ingredients.value.trim();
    if (!ingredients) {
      showError(t("errNoIngredients"), "errNoIngredients");
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
          lang: state.lang,
          warly: els.warly.checked,
          ignoreDried: els.ignoreDried.checked,
          ignoreMilkmade: els.ignoreMilkmade.checked,
          ignoreOverTime: els.ignoreOverTime.checked,
          losses: lossesPayload(),
        }),
      });

      let data;
      try {
        data = await response.json();
      } catch (error) {
        showError(t("errUnreadable"), "errUnreadable");
        return;
      }

      if (!response.ok) {
        showError(data.error || t("errBuild"));
        return;
      }

      render(data);
      els.results.hidden = false;
      if (wasHidden) {
        els.results.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    } catch (error) {
      if (error instanceof TypeError) {
        showError(t("errUnreachable"), "errUnreachable");
      } else {
        showError(error.message || t("errBuild"));
      }
    } finally {
      setLoading(false);
    }
  }

  function chip(stat, value) {
    const node = el("span", `chip ${STAT_CLASS[stat]}`);
    if (Number(value) < -1e-9) node.classList.add("negative");
    node.append(document.createTextNode(statName(stat)));
    node.append(el("b", null, fmt(value)));
    return node;
  }

  function miniStat(stat, value) {
    const node = el("span", Number(value) < -1e-9 ? "mini-stat negative" : "mini-stat");
    node.append(document.createTextNode(`${statName(stat)} `));
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
      container.append(el("span", null, foodName(ingredient)));
    });
  }

  function stepTitle(action) {
    const title = el("div", "step-title");
    const verbKey = STEP_VERB_KEY[action.kind];
    title.append(el("span", "verb", verbKey ? t(verbKey) : action.kind));

    if (action.kind === "cook") {
      title.append(document.createTextNode(action.ingredients.map(foodName).join(", ")));
      title.append(el("span", "arrow", "→"));
      title.append(document.createTextNode(foodName(action.food)));
    } else if (action.kind === "roast" || action.kind === "dry") {
      title.append(document.createTextNode(foodName(action.source)));
      title.append(el("span", "arrow", "→"));
      title.append(document.createTextNode(foodName(action.food)));
    } else {
      title.append(document.createTextNode(foodName(action.food)));
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
      stats.append(el("span", "mini-stat", t("notEaten")));
    } else if (action.kind === "prep") {
      stats.append(el("span", "mini-stat", t("forThePot")));
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

  function renderDishes(data) {
    clear(els.dishesGrid);
    els.dishesCount.textContent = String(data.totalDishes);

    if (!data.dishes.length) {
      els.dishesNote.textContent = t("dishesEmpty");
      return;
    }

    if (data.totalDishes > data.dishes.length) {
      els.dishesNote.textContent = t("dishesTop", {
        shown: data.dishes.length,
        total: data.totalDishes,
        stat: statBy(data.stat),
      });
    } else {
      els.dishesNote.textContent = t("dishesAll", {
        n: data.totalDishes,
        word: countWord(data.totalDishes, "dish"),
        stat: statBy(data.stat),
      });
    }

    data.dishes.forEach((dish) => {
      const card = el("article", "dish");

      const head = el("div", "dish-head");
      head.append(el("span", "dish-name", foodName(dish.name)));
      head.append(
        el("span", "dish-score", `${fmt(dish.score)} ${statUnit(data.stat)}`)
      );

      const stats = el("div", "dish-stats");
      STAT_KEYS.forEach((stat) => {
        stats.append(el("span", null, `${statName(stat)} ${fmt(dish.stats[stat] ?? 0)}`));
      });

      const combo = el("p", "dish-combo", dish.combination.map(foodName).join(" + "));
      card.append(head, stats, combo);
      els.dishesGrid.append(card);
    });

    els.dishesDetails.open = data.totalDishes <= 18;
  }

  function render(data) {
    state.data = data;

    els.summaryStat.textContent = statName(data.stat);
    els.totalValue.textContent = fmt(data.total);
    els.totalUnit.textContent = statUnit(data.stat);

    const steps = data.plan.length;
    const items = data.ingredients.length;
    els.planMode.textContent = t(data.exact ? "planExhaustive" : "planBeam");
    els.planMode.title = t(data.exact ? "planExhaustiveTitle" : "planBeamTitle");

    const meta = [
      `${steps} ${countWord(steps, "step")}`,
      `${items} ${countWord(items, "ingredient")}`,
      t(data.warly ? "metaWarly" : "metaStandard"),
    ];
    if (data.dried) meta.push(t("metaDried"));
    if (data.milkmade) meta.push(t("metaMilkmade"));
    if (data.overTime) meta.push(t("metaOverTime"));
    if (!data.exact) meta.push(t("metaBeam"));
    meta.push(t("metaEngine", { engine: data.engine === "C++" ? "C++" : "Python" }));
    els.planMeta.textContent = meta.join(" · ");

    fillChips(els.totalChips, data.totals);

    const allowed = STAT_KEYS.filter((stat) => Number(data.losses[stat]) > 0);
    if (allowed.length) {
      els.lossSummary.textContent =
        t("lossAllowed") +
        allowed
          .map((stat) => `${statName(stat).toLowerCase()} ${fmt(data.losses[stat])}`)
          .join(", ");
    } else {
      els.lossSummary.textContent = t("lossNone");
    }

    renderPlan(data);

    if (data.bestDish) {
      els.bestCard.hidden = false;
      els.bestName.textContent = foodName(data.bestDish.name);
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

  els.langButtons.forEach((button) => {
    button.addEventListener("click", () => switchLanguage(button.dataset.lang));
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
    els.ingredients.value = t("sample");
    countIngredients();
    setStat("Hunger");
    els.ingredients.focus();
  });

  els.form.addEventListener("submit", calculate);
  els.warly.addEventListener("change", clearError);
  els.ignoreDried.addEventListener("change", clearError);
  els.ignoreMilkmade.addEventListener("change", clearError);
  els.ignoreOverTime.addEventListener("change", clearError);
  els.ingredients.addEventListener("input", clearError);

  async function init() {
    const lang = detectLang();
    if (lang === "ru") await loadRuNames();
    setStat(state.stat);
    applyLanguage(lang);
    loadServerConfig();
  }

  init();
})();
