/*
 * Interface strings for the DSTMeta site.
 *
 * Food and dish names live in names_ru.json and come from the official
 * Russian localization of Don't Starve Together (the same names the Russian
 * wiki uses).  Add a new language here and to SUPPORTED_LANGS in app.js.
 */
window.DSTMETA_I18N = {
  en: {
    title: "DSTMeta — Crockpot Planner",
    metaDescription:
      "Plan the best use of your Don't Starve Together food: crockpot dishes, campfire roasts, drying rack foods, and raw snacks.",
    language: "Language",

    eyebrow: "Chest to plate",
    headline: "Make every ingredient count.",
    heroText:
      "Tell us what is in your chest. We will find the best mix of crockpot " +
      "dishes, campfire roasts, drying rack foods, and raw snacks for the stat " +
      "you care about.",

    ingredientsTitle: "Your ingredients",
    ingredientsLabel: "Ingredients, one per line",
    ingredientsPlaceholder: "Meat\nMeat\nMeat\nIce\nMeat",
    sample: "Meat\nMeat\nMeat\nIce\nMeat",
    hintLead: "One per line, up to",
    hintMid: "items and",
    hintTail: "kinds. Duplicates matter.",
    loadExample: "Load example",

    configTitle: "Config",
    maximize: "Maximize",
    statToMaximize: "Stat to maximize",
    statHunger: "Hunger",
    statSanity: "Sanity",
    statHealth: "Health",

    warlyTitle: "Warly recipes",
    warlySub: "Portable Crock Pot exclusives",
    ignoreDriedTitle: "Ignore Dried variants",
    ignoreDriedSub: "Default: on · skip Jerky and dried kelp",
    ignoreMilkmadeTitle: "Ignore Milkmade Hat",
    ignoreMilkmadeSub: "Default: on · it is worn, not eaten",
    ignoreOverTimeTitle: "Ignore over time stats",
    ignoreOverTimeSub: "Default: on · only instant stat gains",

    lossesTitle: "Permissible losses",
    lossesHelpA: "How much of each stat the whole plan may lose. ",
    lossesHelpB: " means never finish below zero.",
    allowedHungerLoss: "Allowed hunger loss",
    allowedSanityLoss: "Allowed sanity loss",
    allowedHealthLoss: "Allowed health loss",

    calculate: "Calculate plan",
    calculating: "Calculating…",

    bestPlanFor: "Best plan for",
    planTitle: "Plan",
    bestDish: "Best single dish",
    from: "From",
    allDishes: "All cookable dishes",

    howLossesTitle: "How losses work",
    howLossesText:
      "A plan is rejected if any final stat drops below the negative of its " +
      "permissible loss. Keep the defaults at 0 for a no-loss plan, or raise a " +
      "limit to trade one stat for a stronger result in another.",
    consideredTitle: "What gets considered",
    consideredText:
      "Eating raw, roasting first, drying on a rack (unless ignored), keeping " +
      "an item, or cooking four items in the pot. Plans are checked as a " +
      "whole, not dish by dish. Slow, over-time stat gains are skipped unless " +
      "enabled.",

    footerData:
      "Data from the Don't Starve wiki. Not affiliated with Klei Entertainment.",
    footerSmall: "DSTMeta is a working name.",

    itemOne: "item",
    itemFew: "items",
    itemMany: "items",
    stepOne: "step",
    stepFew: "steps",
    stepMany: "steps",
    ingredientOne: "ingredient",
    ingredientFew: "ingredients",
    ingredientMany: "ingredients",
    dishOne: "dish",
    dishFew: "dishes",
    dishMany: "dishes",

    errNoIngredients: "Add at least one ingredient first.",
    errBuild: "The calculator could not build a plan.",
    errUnreadable: "The calculator returned an unreadable response.",
    errUnreachable:
      "Could not reach the calculator. Is the local server running?",

    verbCook: "Cook",
    verbRoast: "Roast",
    verbDry: "Dry",
    verbEat: "Eat",
    verbKeep: "Keep",
    verbPrep: "Prepare",
    notEaten: "not eaten",
    forThePot: "for the pot",

    planExhaustive: "exhaustive",
    planBeam: "beam search",
    planExhaustiveTitle: "Every combination was searched.",
    planBeamTitle:
      "Approximate: only the most promising branches were searched.",

    metaWarly: "Warly recipes included",
    metaStandard: "standard recipes",
    metaDried: "drying rack enabled",
    metaMilkmade: "Milkmade Hat allowed",
    metaOverTime: "over-time stats counted",
    metaBeam: "beam search (approximate)",
    metaEngine: "{engine} engine",

    lossAllowed: "Allowed loss: ",
    lossNone: "No net losses allowed",

    dishesEmpty: "Add at least four ingredients to see crockpot dishes.",
    dishesTop: "Showing the top {shown} of {total} dishes for {stat}.",
    dishesAll: "{n} {word} can be made, ranked by {stat}.",

    statUnitHunger: "hunger",
    statUnitSanity: "sanity",
    statUnitHealth: "health",
    statByHunger: "hunger",
    statBySanity: "sanity",
    statByHealth: "health",
  },

  ru: {
    title: "DSTMeta — планировщик еды",
    metaDescription:
      "Спланируйте, как лучше использовать еду в Don't Starve Together: блюда " +
      "казана, жарка на костре, сушка и сырые перекусы.",
    language: "Язык",

    eyebrow: "Из сундука на тарелку",
    headline: "Пусть каждый ингредиент приносит пользу.",
    heroText:
      "Расскажите, что лежит в сундуке. Мы подберём лучший набор блюд казана, " +
      "жареной еды, сушёных продуктов и сырых перекусов для нужной вам " +
      "характеристики.",

    ingredientsTitle: "Ваши ингредиенты",
    ingredientsLabel: "Ингредиенты, по одному в строке",
    ingredientsPlaceholder: "Мясо\nМясо\nМясо\nЛёд\nМясо",
    sample: "Мясо\nМясо\nМясо\nЛёд\nМясо",
    hintLead: "По одному в строке, до",
    hintMid: "предметов и",
    hintTail: "видов. Дубликаты учитываются.",
    loadExample: "Загрузить пример",

    configTitle: "Настройки",
    maximize: "Максимизировать",
    statToMaximize: "Характеристика для максимизации",
    statHunger: "Голод",
    statSanity: "Рассудок",
    statHealth: "Здоровье",

    warlyTitle: "Рецепты Варли",
    warlySub: "Только для переносного казана",
    ignoreDriedTitle: "Игнорировать вяленые варианты",
    ignoreDriedSub: "По умолчанию: вкл. · без джерки и сушёных водорослей",
    ignoreMilkmadeTitle: "Игнорировать молочную шапку",
    ignoreMilkmadeSub: "По умолчанию: вкл. · её носят, а не едят",
    ignoreOverTimeTitle: "Игнорировать постепенные эффекты",
    ignoreOverTimeSub: "По умолчанию: вкл. · только мгновенные эффекты",

    lossesTitle: "Допустимые потери",
    lossesHelpA:
      "Сколько единиц каждой характеристики может потерять весь план. ",
    lossesHelpB: " — не опускаться ниже нуля.",
    allowedHungerLoss: "Допустимая потеря голода",
    allowedSanityLoss: "Допустимая потеря рассудка",
    allowedHealthLoss: "Допустимая потеря здоровья",

    calculate: "Рассчитать план",
    calculating: "Расчёт…",

    bestPlanFor: "Лучший план:",
    planTitle: "План",
    bestDish: "Лучшее блюдо",
    from: "Из",
    allDishes: "Все доступные блюда",

    howLossesTitle: "Как работают потери",
    howLossesText:
      "План отклоняется, если любая итоговая характеристика опускается ниже " +
      "допустимой потери со знаком минус. Оставьте значения по умолчанию (0), " +
      "чтобы обойтись без потерь, или увеличьте лимит, чтобы обменять одну " +
      "характеристику на лучший результат в другой.",
    consideredTitle: "Что учитывается",
    consideredText:
      "Съесть сырым, сначала пожарить, высушить на сушилке (если не " +
      "отключено), оставить предмет или приготовить четыре ингредиента в " +
      "казане. План проверяется целиком, а не по одному блюду. Постепенные " +
      "эффекты пропускаются, если их не включить.",

    footerData: "Данные с вики Don't Starve. Не связано с Klei Entertainment.",
    footerSmall: "DSTMeta — рабочее название.",

    itemOne: "предмет",
    itemFew: "предмета",
    itemMany: "предметов",
    stepOne: "шаг",
    stepFew: "шага",
    stepMany: "шагов",
    ingredientOne: "ингредиент",
    ingredientFew: "ингредиента",
    ingredientMany: "ингредиентов",
    dishOne: "блюдо",
    dishFew: "блюда",
    dishMany: "блюд",

    errNoIngredients: "Сначала добавьте хотя бы один ингредиент.",
    errBuild: "Калькулятор не смог составить план.",
    errUnreadable: "Калькулятор вернул нечитаемый ответ.",
    errUnreachable:
      "Не удалось связаться с калькулятором. Локальный сервер запущен?",

    verbCook: "Сготовить",
    verbRoast: "Пожарить",
    verbDry: "Высушить",
    verbEat: "Съесть",
    verbKeep: "Оставить",
    verbPrep: "Подготовить",
    notEaten: "не съедено",
    forThePot: "для казана",

    planExhaustive: "полный перебор",
    planBeam: "лучевой поиск",
    planExhaustiveTitle: "Проверены все комбинации.",
    planBeamTitle:
      "Приближённо: проверены только самые перспективные ветки.",

    metaWarly: "с рецептами Варли",
    metaStandard: "обычные рецепты",
    metaDried: "сушка включена",
    metaMilkmade: "молочная шапка разрешена",
    metaOverTime: "постепенные эффекты учтены",
    metaBeam: "лучевой поиск (приближённо)",
    metaEngine: "движок {engine}",

    lossAllowed: "Допустимая потеря: ",
    lossNone: "Без потерь",

    dishesEmpty:
      "Добавьте хотя бы четыре ингредиента, чтобы увидеть блюда казана.",
    dishesTop: "Показаны лучшие {shown} из {total} блюд: {stat}.",
    dishesAll: "Можно приготовить {n} {word}. Сортировка: {stat}.",

    statUnitHunger: "голода",
    statUnitSanity: "рассудка",
    statUnitHealth: "здоровья",
    statByHunger: "по голоду",
    statBySanity: "по рассудку",
    statByHealth: "по здоровью",
  },
};
