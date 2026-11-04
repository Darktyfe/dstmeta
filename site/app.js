(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const I18N = window.DSTMETA_I18N || { en: {} };

  const els = {
    form: $("#planner"),
    picker: $("#ingredient-picker"),
    pickerEmpty: $("#picker-empty"),
    pickerMessage: $("#picker-message"),
    search: $("#ingredient-search"),
    clearPicker: $("#clear-picker"),
    itemCount: $("#item-count"),
    maxIngredients: $("#max-ingredients"),
    maxTypes: $("#max-types"),
    sample: $("#sample"),
    langButtons: $$(".lang-switch button"),
    settingsToggle: $("#settings-toggle"),
    settingsPanel: $("#settings-panel"),
    settingsClose: $("#settings-close"),
    characterToggle: $("#character-toggle"),
    characterPortrait: $("#character-portrait"),
    characterName: $("#character-name"),
    characterMenu: $("#character-menu"),
    warlyRepeatsWrap: $("#warly-repeats-wrap"),
    warlyRepeats: $("#warly-repeats"),
    modeToggle: $("#uncompromising-toggle"),
    statButtons: $$(".segmented button"),
    warly: $("#warly"),
    ignoreDried: $("#ignore-dried"),
    ignoreMilkmade: $("#ignore-milkmade"),
    ignoreOverTime: $("#ignore-over-time"),
    ignoreOverTimeRow: $("#ignore-over-time-row"),
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
    mode: "dst",
    character: "wilson",
    warlyRepeats: 1,
    stat: "Hunger",
    loading: false,
    data: null,
    errorKey: null,
    foods: [],
    counts: new Map(),
    tileRefs: new Map(),
    loaded: false,
    loadFailed: false,
    maxIngredients: 100,
    maxTypes: 24,
  };

  const STAT_KEYS = ["Hunger", "Sanity", "Health"];
  const STAT_CLASS = { Hunger: "hunger", Sanity: "sanity", Health: "health" };
  const STEP_ICON = {
    cook: "🍲", roast: "🔥", dry: "🥓", eat: "🍴", keep: "✋", prep: "🔪", kill: "🗡️",
  };
  const STEP_VERB_KEY = {
    cook: "verbCook",
    roast: "verbRoast",
    dry: "verbDry",
    eat: "verbEat",
    keep: "verbKeep",
    prep: "verbPrep",
    kill: "verbKill",
  };

  const CHARACTERS = [
    { id: "wilson", key: "charWilson" },
    { id: "willow", key: "charWillow" },
    { id: "wolfgang", key: "charWolfgang" },
    { id: "wendy", key: "charWendy" },
    { id: "wx-78", key: "charWX78" },
    { id: "wickerbottom", key: "charWickerbottom" },
    { id: "woodie", key: "charWoodie" },
    { id: "wes", key: "charWes" },
    { id: "maxwell", key: "charMaxwell" },
    { id: "wigfrid", key: "charWigfrid" },
    { id: "webber", key: "charWebber" },
    { id: "winona", key: "charWinona" },
    { id: "warly", key: "charWarly" },
    { id: "walter", key: "charWalter" },
    { id: "wortox", key: "charWortox" },
    { id: "wormwood", key: "charWormwood" },
    { id: "wurt", key: "charWurt" },
    { id: "wanda", key: "charWanda" },
    { id: "wonkey", key: "charWonkey" },
    { id: "winky", key: "charWinky", mode: "uc" },
    { id: "wathom", key: "charWathom", mode: "uc" },
    { id: "wixie", key: "charWixie", mode: "uc" },
  ];

  const SAMPLE = ["Meat", "Meat", "Meat", "Ice", "Meat"];

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

  function storedMode() {
    try {
      const saved = localStorage.getItem("dstmeta.mode");
      return saved === "dst" || saved === "uc" ? saved : null;
    } catch (error) {
      return null;
    }
  }

  function applyMode(mode) {
    state.mode = mode === "uc" ? "uc" : "dst";
    try {
      localStorage.setItem("dstmeta.mode", state.mode);
    } catch (error) {
      // Storage may be unavailable; the mode still works for this page.
    }
    const uncompromising = state.mode === "uc";
    document.body.classList.toggle("uncompromising", uncompromising);
    if (els.modeToggle) {
      els.modeToggle.setAttribute(
        "aria-pressed",
        uncompromising ? "true" : "false",
      );
    }
    // Uncompromising Mode always counts gradual Health/Sanity restoration,
    // so the switch is not offered there.
    if (els.ignoreOverTimeRow) {
      els.ignoreOverTimeRow.hidden = uncompromising;
    }
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
  function iconSlug(name) {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function totalItems() {
    let total = 0;
    state.counts.forEach((count) => {
      total += count;
    });
    return total;
  }

  function countIngredients() {
    const total = totalItems();
    els.itemCount.textContent = `${total} ${countWord(total, "item")}`;
  }

  function serializeIngredients() {
    const names = [];
    state.counts.forEach((count, name) => {
      for (let index = 0; index < count; index += 1) names.push(name);
    });
    return names.join("\n");
  }

  function setPickerMessage(text) {
    els.pickerMessage.textContent = text || "";
    els.pickerMessage.hidden = !text;
  }

  function refreshTile(name) {
    const ref = state.tileRefs.get(name);
    if (!ref) return;
    const count = state.counts.get(name) || 0;
    ref.tile.classList.toggle("selected", count > 0);
    ref.badge.textContent = String(count);
    ref.badge.hidden = count === 0;
    ref.badge.title = t("pickerRemove", { name: foodName(name), count });
    ref.badge.setAttribute("aria-label", ref.badge.title);
    ref.add.title = foodName(name);
    ref.add.setAttribute("aria-label", t("pickerAdd", { name: foodName(name) }));
  }

  function refreshAllTiles() {
    state.tileRefs.forEach((_, name) => refreshTile(name));
  }

  function applyFilter() {
    const query = (els.search.value || "").trim().toLowerCase();
    let matches = 0;
    state.tileRefs.forEach((ref, name) => {
      const localised = (ruNames && ruNames[name]) || "";
      const haystack = `${name}\n${localised}`.toLowerCase();
      const visible = !query || haystack.includes(query);
      ref.tile.hidden = !visible;
      if (visible) matches += 1;
    });
    els.pickerEmpty.hidden = !query || matches > 0;
  }

  function refreshPickerLabels() {
    refreshAllTiles();
    applyFilter();
  }

  function addIngredient(name) {
    if (totalItems() >= state.maxIngredients) {
      setPickerMessage(t("pickerLimitItems", { max: state.maxIngredients }));
      return;
    }
    const count = state.counts.get(name) || 0;
    if (count === 0 && state.counts.size >= state.maxTypes) {
      setPickerMessage(t("pickerLimitTypes", { max: state.maxTypes }));
      return;
    }
    state.counts.set(name, count + 1);
    setPickerMessage("");
    refreshTile(name);
    countIngredients();
    clearError();
  }

  function removeIngredient(name) {
    const count = state.counts.get(name) || 0;
    if (count <= 0) return;
    if (count === 1) state.counts.delete(name);
    else state.counts.set(name, count - 1);
    setPickerMessage("");
    refreshTile(name);
    countIngredients();
    clearError();
  }

  function clearIngredients() {
    state.counts.clear();
    setPickerMessage("");
    refreshAllTiles();
    countIngredients();
    clearError();
  }

  function loadSample() {
    if (!state.loaded) return;
    state.counts.clear();
    SAMPLE.forEach((name) => {
      state.counts.set(name, (state.counts.get(name) || 0) + 1);
    });
    setPickerMessage("");
    refreshAllTiles();
    countIngredients();
    clearError();
    setStat("Hunger");
  }

  function tileNode(name) {
    const tile = el("div", "ingredient-tile");
    tile.dataset.food = name;

    const add = el("button", "tile-add");
    add.type = "button";
    add.title = foodName(name);
    add.setAttribute("aria-label", t("pickerAdd", { name: foodName(name) }));

    const image = document.createElement("img");
    image.className = "tile-icon";
    image.src = `icons/${iconSlug(name)}.png`;
    image.alt = "";
    image.width = 64;
    image.height = 64;
    image.loading = "lazy";
    image.decoding = "async";
    image.addEventListener("error", () => {
      image.remove();
      add.classList.add("tile-add-missing");
      add.append(el("span", "tile-fallback", "?"));
    });
    add.append(image);

    add.addEventListener("click", () => addIngredient(name));
    add.addEventListener("keydown", (event) => {
      if (event.key === "Backspace" || event.key === "Delete" || event.key === "-") {
        event.preventDefault();
        removeIngredient(name);
      }
    });

    const badge = el("button", "tile-count");
    badge.type = "button";
    badge.hidden = true;
    badge.textContent = "0";
    badge.addEventListener("click", (event) => {
      event.stopPropagation();
      removeIngredient(name);
    });

    tile.addEventListener("contextmenu", (event) => {
      event.preventDefault();
      removeIngredient(name);
    });

    tile.append(add, badge);
    state.tileRefs.set(name, { tile, add, badge });
    refreshTile(name);
    return tile;
  }

  function buildPicker() {
    clear(els.picker);
    state.tileRefs.clear();

    const grid = el("div", "ingredient-grid");
    state.foods.forEach((name) => grid.append(tileNode(name)));
    els.picker.append(grid);

    applyFilter();
    countIngredients();
  }

  function showPickerLoadError() {
    state.loadFailed = true;
    clear(els.picker);
    const message = el("p", "picker-load-error");
    message.append(document.createTextNode(t("pickerLoadFailed") + " "));
    const retry = el("button", "link-button", t("pickerRetry"));
    retry.type = "button";
    retry.addEventListener("click", loadFoods);
    message.append(retry);
    els.picker.append(message);
    els.pickerEmpty.hidden = true;
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
    $$("[data-i18n-title]").forEach((node) => {
      node.title = t(node.dataset.i18nTitle);
    });

    refreshCharacterLabels();

    els.langButtons.forEach((button) => {
      const active = button.dataset.lang === state.lang;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });

    countIngredients();

    // Re-render picker state in the new language.
    if (state.loadFailed) {
      showPickerLoadError();
    } else {
      refreshPickerLabels();
    }
  }

  async function switchLanguage(lang) {
    if (lang === state.lang) return;
    if (!state.errorKey) clearError();
    if (lang === "ru") {
      await loadRuNames();
    }
    applyLanguage(lang);
  }

  async function loadFoods() {
    state.loadFailed = false;
    clear(els.picker);
    els.picker.append(el("p", "picker-loading", t("pickerLoading")));
    els.pickerEmpty.hidden = true;
    try {
      const response = await fetch(
        `/api/foods?mode=${encodeURIComponent(state.mode)}`,
        { cache: "no-store" },
      );
      if (!response.ok) throw new Error("foods");
      const data = await response.json();
      state.foods = Array.isArray(data.foods) ? data.foods.slice() : [];
      if (data.mode === "dst" || data.mode === "uc") state.mode = data.mode;
      pruneIngredientCounts();
      if (Number.isFinite(data.maxIngredients)) {
        state.maxIngredients = data.maxIngredients;
        els.maxIngredients.textContent = String(data.maxIngredients);
      }
      if (Number.isFinite(data.maxIngredientTypes)) {
        state.maxTypes = data.maxIngredientTypes;
        els.maxTypes.textContent = String(data.maxIngredientTypes);
      }
      state.loaded = true;
      buildPicker();
    } catch (error) {
      state.loaded = false;
      showPickerLoadError();
    }
  }

  function pruneIngredientCounts() {
    const available = new Set(state.foods);
    Array.from(state.counts.keys()).forEach((name) => {
      if (!available.has(name)) state.counts.delete(name);
    });
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
    $$("[data-i18n-title]").forEach((node) => {
      node.title = t(node.dataset.i18nTitle);
    });

    refreshCharacterLabels();

    els.langButtons.forEach((button) => {
      const active = button.dataset.lang === state.lang;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });

    countIngredients();
    setPickerMessage("");
    if (state.loaded) refreshPickerLabels();
    else if (state.loadFailed) showPickerLoadError();
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

  function settingsOpen() {
    return Boolean(els.settingsPanel) && !els.settingsPanel.hidden;
  }

  function openSettings() {
    if (!els.settingsPanel || settingsOpen()) return;
    els.settingsPanel.hidden = false;
    els.settingsToggle.setAttribute("aria-expanded", "true");
    els.settingsPanel.focus();
  }

  function closeSettings(restoreFocus = true) {
    if (!settingsOpen()) return;
    closeCharacterMenu(false);
    els.settingsPanel.hidden = true;
    els.settingsToggle.setAttribute("aria-expanded", "false");
    if (restoreFocus) els.settingsToggle.focus();
  }

  function toggleSettings() {
    if (settingsOpen()) closeSettings();
    else openSettings();
  }

  function characterLabel(character) {
    return t(character.key);
  }

  function characterById(id) {
    return CHARACTERS.find((character) => character.id === id) || null;
  }

  function availableCharacters() {
    return CHARACTERS.filter(
      (character) => !character.mode || character.mode === state.mode
    );
  }

  function activeCharacter() {
    return (
      availableCharacters().find(
        (character) => character.id === state.character
      ) || availableCharacters()[0]
    );
  }

  function storedCharacter() {
    try {
      const saved = localStorage.getItem("dstmeta.character");
      return availableCharacters().some(
        (character) => character.id === saved
      )
        ? saved
        : null;
    } catch (error) {
      return null;
    }
  }

  function storedWarlyRepeats() {
    try {
      const raw = localStorage.getItem("dstmeta.warlyRepeats");
      if (raw === null || raw === "") return null;
      const saved = Number(raw);
      return Number.isInteger(saved) && saved >= -1 && saved <= 5
        ? saved
        : null;
    } catch (error) {
      return null;
    }
  }

  function applyWarlyRepeats(value) {
    const number = Number(value);
    state.warlyRepeats =
      Number.isInteger(number) && number >= -1 && number <= 5 ? number : 1;
    if (els.warlyRepeats) {
      els.warlyRepeats.value = String(state.warlyRepeats);
    }
    try {
      localStorage.setItem(
        "dstmeta.warlyRepeats", String(state.warlyRepeats)
      );
    } catch (error) {
      // Storage may be unavailable; the setting still works for this page.
    }
    refreshWarlyRepeats();
  }

  function refreshWarlyRepeats() {
    if (!els.warlyRepeatsWrap) return;
    els.warlyRepeatsWrap.hidden = state.character !== "warly";
  }

  function buildCharacterMenu() {
    if (!els.characterMenu) return;
    clear(els.characterMenu);
    let modGroup = false;
    availableCharacters().forEach((character) => {
      if (character.mode === "uc" && !modGroup) {
        modGroup = true;
        const label = el("div", "character-group-label", t("uncompromising"));
        label.setAttribute("role", "presentation");
        els.characterMenu.append(label);
      }

      const option = el("button", "character-option");
      option.type = "button";
      option.dataset.character = character.id;
      option.setAttribute("role", "option");
      option.tabIndex = -1;

      const image = document.createElement("img");
      image.className = "character-option-portrait";
      image.src = `portraits/${character.id}.png`;
      image.alt = "";
      image.width = 26;
      image.height = 26;
      image.loading = "lazy";
      image.decoding = "async";

      option.append(
        image,
        el("span", "character-option-name", characterLabel(character))
      );
      option.addEventListener("click", () => selectCharacter(character.id));
      els.characterMenu.append(option);
    });
    markCharacterOptions();
  }

  function markCharacterOptions() {
    if (!els.characterMenu) return;
    $$(".character-option", els.characterMenu).forEach((option) => {
      const selected = option.dataset.character === state.character;
      option.setAttribute("aria-selected", selected ? "true" : "false");
      option.tabIndex = selected ? 0 : -1;
    });
  }

  function refreshCharacterLabels() {
    if (!els.characterToggle) return;
    const character = activeCharacter();
    els.characterName.textContent = characterLabel(character);
    els.characterToggle.title = characterLabel(character);
    if (!els.characterMenu) return;
    $$(".character-option", els.characterMenu).forEach((option) => {
      const found = CHARACTERS.find(
        (item) => item.id === option.dataset.character
      );
      const name = option.querySelector(".character-option-name");
      if (found && name) name.textContent = characterLabel(found);
    });
    const group = els.characterMenu.querySelector(".character-group-label");
    if (group) group.textContent = t("uncompromising");
  }

  function applyCharacter(id) {
    const character =
      CHARACTERS.find((item) => item.id === id) || CHARACTERS[0];
    state.character = character.id;
    try {
      localStorage.setItem("dstmeta.character", character.id);
    } catch (error) {
      // Storage may be unavailable; the selection still works for this page.
    }
    if (els.characterPortrait) {
      els.characterPortrait.src = `portraits/${character.id}.png`;
    }
    refreshCharacterLabels();
    markCharacterOptions();
    refreshWarlyRepeats();
  }

  function refreshCharacterMode() {
    const available = availableCharacters();
    if (!available.some((character) => character.id === state.character)) {
      applyCharacter(available[0].id);
    }
    closeCharacterMenu(false);
    buildCharacterMenu();
  }

  function characterMenuOpen() {
    return Boolean(els.characterMenu) && !els.characterMenu.hidden;
  }

  function positionCharacterMenu() {
    if (!characterMenuOpen()) return;
    const rect = els.characterToggle.getBoundingClientRect();
    const margin = 12;
    const width = Math.min(300, window.innerWidth - margin * 2);
    els.characterMenu.style.width = `${width}px`;

    let left = rect.right - width;
    left = Math.max(margin, Math.min(left, window.innerWidth - margin - width));

    let top = rect.bottom + 8;
    let maxHeight = Math.min(500, window.innerHeight - top - margin);
    const spaceAbove = rect.top - margin - 8;
    if (maxHeight < 220 && spaceAbove > maxHeight) {
      maxHeight = Math.min(500, spaceAbove);
      top = rect.top - 8 - maxHeight;
    }

    els.characterMenu.style.left = `${Math.round(left)}px`;
    els.characterMenu.style.top = `${Math.round(top)}px`;
    els.characterMenu.style.maxHeight =
      `${Math.max(120, Math.round(maxHeight))}px`;
  }

  function openCharacterMenu(focusLast = false) {
    if (!els.characterMenu) return;
    if (!els.characterMenu.children.length) buildCharacterMenu();
    markCharacterOptions();
    els.characterMenu.hidden = false;
    els.characterToggle.setAttribute("aria-expanded", "true");
    positionCharacterMenu();
    const options = $$(".character-option", els.characterMenu);
    const selected = options.find(
      (option) => option.dataset.character === state.character
    );
    const target = focusLast
      ? options[options.length - 1]
      : selected || options[0];
    if (target) target.focus();
  }

  function closeCharacterMenu(restoreFocus = true) {
    if (!characterMenuOpen()) return;
    els.characterMenu.hidden = true;
    els.characterToggle.setAttribute("aria-expanded", "false");
    if (restoreFocus) els.characterToggle.focus();
  }

  function toggleCharacterMenu() {
    if (characterMenuOpen()) closeCharacterMenu();
    else openCharacterMenu();
  }

  function selectCharacter(id) {
    applyCharacter(id);
    closeCharacterMenu();
  }

  function focusCharacterOption(step) {
    const options = $$(".character-option", els.characterMenu);
    if (!options.length) return;
    const current = options.indexOf(document.activeElement);
    const next =
      current === -1
        ? step > 0
          ? 0
          : options.length - 1
        : (current + step + options.length) % options.length;
    options[next].focus();
  }

  function onCharacterMenuKey(event) {
    const options = $$(".character-option", els.characterMenu);
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        focusCharacterOption(1);
        break;
      case "ArrowUp":
        event.preventDefault();
        focusCharacterOption(-1);
        break;
      case "Home":
        event.preventDefault();
        if (options.length) options[0].focus();
        break;
      case "End":
        event.preventDefault();
        if (options.length) options[options.length - 1].focus();
        break;
      case "Enter":
      case " ":
        event.preventDefault();
        if (document.activeElement.classList.contains("character-option")) {
          selectCharacter(document.activeElement.dataset.character);
        }
        break;
      case "Escape":
        event.preventDefault();
        event.stopPropagation();
        closeCharacterMenu();
        break;
      case "Tab":
        event.preventDefault();
        closeCharacterMenu();
        break;
      default:
        break;
    }
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

    const ingredients = serializeIngredients();
    if (!ingredients) {
      showError(t("errNoIngredients"), "errNoIngredients");
      els.search.focus();
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
          mode: state.mode,
          character: state.character,
          warlyRepeats: state.warlyRepeats,
          warly: els.warly.checked,
          ignoreDried: els.ignoreDried.checked,
          ignoreMilkmade: els.ignoreMilkmade.checked,
          // Gradual stats are always counted in Uncompromising Mode.
          ignoreOverTime:
            state.mode === "uc" ? false : els.ignoreOverTime.checked,
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
      closeSettings(false);
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
    } else if (action.kind === "roast" || action.kind === "dry" || action.kind === "kill") {
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
    } else if (action.kind === "kill") {
      stats.append(el("span", "mini-stat", t("prepared")));
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
    if (data.mode === "uc") meta.push(t("metaUncompromising"));
    if (!data.exact) meta.push(t("metaBeam"));
    if (data.character) {
      const character = characterById(data.character);
      if (character) meta.push(characterLabel(character));
      if (
        data.character === "warly" &&
        Number.isInteger(data.warlyRepeats) &&
        data.warlyRepeats >= 0
      ) {
        meta.push(t("metaWarlyRepeats", { n: data.warlyRepeats }));
      }
    }
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

  els.search.addEventListener("input", () => {
    applyFilter();
    clearError();
  });
  els.search.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      els.form.requestSubmit();
    }
    if (event.key === "Escape" && els.search.value) {
      els.search.value = "";
      applyFilter();
    }
  });

  els.clearPicker.addEventListener("click", () => {
    if (state.counts.size) clearIngredients();
  });

  els.langButtons.forEach((button) => {
    button.addEventListener("click", () => switchLanguage(button.dataset.lang));
  });

  if (els.settingsToggle && els.settingsPanel) {
    els.settingsToggle.addEventListener("click", toggleSettings);
    els.settingsClose.addEventListener("click", () => closeSettings());
    els.settingsPanel.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        closeSettings();
      }
    });
    document.addEventListener("pointerdown", (event) => {
      if (!settingsOpen()) return;
      if (els.settingsPanel.contains(event.target)) return;
      if (els.settingsToggle.contains(event.target)) return;
      if (els.characterMenu && els.characterMenu.contains(event.target)) return;
      closeSettings(false);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape" || !settingsOpen()) return;
      if (els.settingsPanel.contains(document.activeElement)) return;
      closeSettings(false);
    });
  }

  if (els.warlyRepeats) {
    els.warlyRepeats.addEventListener("change", () => {
      applyWarlyRepeats(els.warlyRepeats.value);
      clearError();
    });
  }

  if (els.characterToggle && els.characterMenu) {
    els.characterToggle.addEventListener("click", toggleCharacterMenu);
    els.characterToggle.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        openCharacterMenu(event.key === "ArrowUp");
      }
    });
    els.characterMenu.addEventListener("keydown", onCharacterMenuKey);
    document.addEventListener("pointerdown", (event) => {
      if (!characterMenuOpen()) return;
      if (els.characterMenu.contains(event.target)) return;
      if (els.characterToggle.contains(event.target)) return;
      closeCharacterMenu(false);
    });
    window.addEventListener("resize", () => {
      if (characterMenuOpen()) positionCharacterMenu();
    });
    window.addEventListener("scroll", () => closeCharacterMenu(false), {
      passive: true,
    });
    if (els.settingsPanel) {
      els.settingsPanel.addEventListener("scroll", () => closeCharacterMenu(false), {
        passive: true,
      });
    }
  }

  els.modeToggle.addEventListener("click", () => {
    applyMode(state.mode === "uc" ? "dst" : "uc");
    refreshCharacterMode();
    clearError();
    state.data = null;
    els.results.hidden = true;
    loadFoods();
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
    loadSample();
  });

  els.form.addEventListener("submit", calculate);
  els.warly.addEventListener("change", clearError);
  els.ignoreDried.addEventListener("change", clearError);
  els.ignoreMilkmade.addEventListener("change", clearError);
  els.ignoreOverTime.addEventListener("change", clearError);

  async function init() {
    const lang = detectLang();
    applyMode(storedMode() || "dst");
    buildCharacterMenu();
    applyCharacter(storedCharacter() || "wilson");
    applyWarlyRepeats(storedWarlyRepeats() ?? 1);
    // Russian names are also used by the picker's search box, so load them
    // even when the interface starts in English.
    await loadRuNames();
    setStat(state.stat);
    applyLanguage(lang);
    loadFoods();
  }

  init();
})();
