import type { Locale } from "./locale";

export type RecErrorShort = {
  need_sync: string;
  need_books: string;
  need_enrich: string;
  other: string;
};

export type Messages = {
  nav: {
    brand: string;
    library: string;
    recommendations: string;
    profile: string;
    settings: string;
    ariaMainNav: string;
  };
  library: {
    title: string;
    search: string;
    searchTitle: string;
    import_: string;
    importing: string;
    importAria: string;
    importSuccess: (total: number, bookWord: string) => string;
    importFailed: (detail: string) => string;
    empty: string;
    importMd: string;
    getRecommendations: string;
    addBook: string;
    addBookAria: string;
    addBookDialogAria: string;
    addBookTitleLabel: string;
    addBookAuthorLabel: string;
    addBookRatingLabel: string;
    addBookRatingNone: string;
    addBookNotesLabel: string;
    addBookNotesPlaceholder: string;
    addBookSubmit: string;
    addBookSaving: string;
    addBookSuccess: string;
    addBookFailed: (detail: string) => string;
    addBookEmptyField: string;
    sortAria: string;
    sortDefault: string;
    sortTitle: string;
    sortRating: string;
    sortAdded: string;
    plannedListShort: string;
    blacklistListShort: string;
    plannedListOpenAria: string;
    blacklistListOpenAria: string;
    plannedListTitle: string;
    blacklistTitle: string;
    plannedListDialogAria: string;
    blacklistListDialogAria: string;
    readingListEmpty: string;
    readingListLoading: string;
    removeFromListAria: (title: string) => string;
    readingListLoadError: (detail: string) => string;
  };
  search: {
    aria: string;
    placeholder: string;
    found: (n: number, bookWord: string) => string;
    noResults: string;
  };
  pagination: {
    aria: string;
    prev: string;
    next: string;
    pageWord: string;
    ofWord: string;
  };
  bookCard: {
    openAria: (title: string, author: string) => string;
    ratingAria: (rating: number) => string;
  };
  bookPanel: {
    loadFailed: string;
    saved: string;
    saveFailed: string;
    saveConflict: string;
    fieldTitle: string;
    fieldAuthor: string;
    ratingLabel: string;
    clearRating: string;
    ratingValueAria: (n: number) => string;
    deleted: string;
    deleteFailed: string;
    dialogAria: (title: string) => string;
    dialogFallbackAria: string;
    closeAria: string;
    notes: string;
    edit: string;
    cancel: string;
    saving: string;
    save: string;
    emptyNotes: string;
    confirmDelete: string;
    delete: string;
    deleteBook: string;
  };
  rec: {
    title: string;
    load: string;
    wait: string;
    refresh: string;
    blockedEmpty: string;
    syncLibrary: string;
    blockedMoreBooks: string;
    openLibrary: string;
    blockedEnrich: string;
    enrichCta: string;
    details: string;
    empty: string;
    match: string;
    matchAria: (pct: number) => string;
    savePlannedTitle: string;
    removePlannedTitle: string;
    saveBlacklistTitle: string;
    removeBlacklistTitle: string;
    recListActionError: (detail: string) => string;
    fromCache: string;
    fresh: string;
    preparingEnrich: string;
    preparingRecs: string;
    checkingLibrary: string;
    wittyPhrases: string[];
    errorShort: RecErrorShort;
  };
  profile: {
    loadFailed: (msg: string) => string;
    ready: string;
    prepareFailed: (msg: string) => string;
    rebuilt: string;
    rebuildFailed: (msg: string) => string;
    preparingEnrich: string;
    preparingRecs: string;
    title: string;
    rebuild: string;
    rebuilding: string;
    emptyTitle: string;
    prepareCta: string;
    emptySubBefore: string;
    emptySubLink: string;
    emptySubAfter: string;
    summary: string;
    noSummary: string;
    topGenres: string;
    topThemes: string;
    moods: string;
    favoriteAuthors: string;
    noData: string;
    tagBarAria: (name: string, pct: number) => string;
    authorBarAria: (name: string, rank: number, total: number) => string;
  };
  settings: {
    title: string;
    apiKey: string;
    baseUrl: string;
    modelOnline: string;
    modelOffline: string;
    presets: string;
    testConnection: string;
    testing: string;
    testSuccess: string;
    testFailed: (msg: string) => string;
    save: string;
    saving: string;
    saved: string;
    saveFailed: (msg: string) => string;
    showKey: string;
    hideKey: string;
  };
};

const ru: Messages = {
  nav: {
    brand: "My Bookshelf AI",
    library: "Библиотека",
    recommendations: "Рекомендации",
    profile: "Профиль",
    settings: "Настройки",
    ariaMainNav: "Основная навигация",
  },
  library: {
    title: "Библиотека",
    search: "Поиск",
    searchTitle: "Поиск (Ctrl+O)",
    import_: "Импорт",
    importing: "Импорт…",
    importAria: "Импортировать .md файлы в библиотеку",
    importSuccess: (total, w) => `Импортировано ${total} ${w}`,
    importFailed: (d) => `Импорт не удался: ${d}`,
    empty: "Пока нет книг.",
    importMd: "Импортировать .md файлы",
    getRecommendations: "Получить рекомендации",
    addBook: "Добавить книгу",
    addBookAria: "Добавить книгу в библиотеку",
    addBookDialogAria: "Добавить книгу",
    addBookTitleLabel: "Название",
    addBookAuthorLabel: "Автор",
    addBookRatingLabel: "Оценка",
    addBookRatingNone: "Без оценки",
    addBookNotesLabel: "Заметки",
    addBookNotesPlaceholder: "Необязательно…",
    addBookSubmit: "Добавить",
    addBookSaving: "Добавление…",
    addBookSuccess: "Книга добавлена",
    addBookFailed: (d) => `Не удалось добавить: ${d}`,
    addBookEmptyField: "Укажите название и автора.",
    sortAria: "Порядок книг в списке",
    sortDefault: "Как в библиотеке",
    sortTitle: "По алфавиту",
    sortRating: "По рейтингу",
    sortAdded: "По дате добавления",
    plannedListShort: "К прочтению",
    blacklistListShort: "Чёрный список",
    plannedListOpenAria: "Список книг к прочтению",
    blacklistListOpenAria: "Чёрный список рекомендаций",
    plannedListTitle: "К прочтению",
    blacklistTitle: "Чёрный список",
    plannedListDialogAria: "Список запланированных к чтению книг",
    blacklistListDialogAria: "Чёрный список книг",
    readingListEmpty: "Пока пусто.",
    readingListLoading: "Загрузка…",
    removeFromListAria: (title) => `Убрать «${title}» из списка`,
    readingListLoadError: (d) => `Не удалось загрузить список: ${d}`,
  },
  search: {
    aria: "Поиск по книгам",
    placeholder: "Поиск по названию или автору…",
    found: (n, w) => `Найдено ${n} ${w}`,
    noResults: "Ничего не найдено.",
  },
  pagination: {
    aria: "Страницы",
    prev: "Назад",
    next: "Вперёд",
    pageWord: "Страница",
    ofWord: "из",
  },
  bookCard: {
    openAria: (title, author) => `Открыть «${title}», автор ${author}`,
    ratingAria: (rating) => `Оценка: ${rating} из 5`,
  },
  bookPanel: {
    loadFailed: "Не удалось загрузить данные книги",
    saved: "Сохранено",
    saveFailed: "Не удалось сохранить",
    saveConflict:
      "Книга с таким названием и автором уже есть. Измените данные или объедините записи вручную.",
    fieldTitle: "Название",
    fieldAuthor: "Автор",
    ratingLabel: "Оценка",
    clearRating: "Без оценки",
    ratingValueAria: (n) => `Оценка ${n} из 5`,
    deleted: "Книга удалена",
    deleteFailed: "Не удалось удалить",
    dialogAria: (title) => `Книга: ${title}`,
    dialogFallbackAria: "Сведения о книге",
    closeAria: "Закрыть панель",
    notes: "Заметки",
    edit: "Редактировать",
    cancel: "Отмена",
    saving: "Сохранение…",
    save: "Сохранить",
    emptyNotes:
      "Заметок пока нет. Нажмите «Редактировать», чтобы добавить.",
    confirmDelete: "Удалить эту книгу?",
    delete: "Удалить",
    deleteBook: "Удалить книгу",
  },
  rec: {
    title: "Рекомендации",
    load: "Загрузить",
    wait: "Подождите…",
    refresh: "Обновить",
    blockedEmpty: "Здесь пока пустая библиотека.",
    syncLibrary: "Синхронизировать библиотеку",
    blockedMoreBooks:
      "Добавьте ещё одну книгу и снова синхронизируйте.",
    openLibrary: "Открыть библиотеку",
    blockedEnrich:
      "Остался шаг: проанализируйте книги, затем загрузите подборку.",
    enrichCta: "Проанализировать и показать подборку",
    details: "Подробности",
    empty: "Рекомендаций не получено.",
    match: "Совпадение",
    matchAria: (pct) => `Совпадение: ${pct} процентов`,
    savePlannedTitle: "В список к прочтению",
    removePlannedTitle: "Убрать из списка к прочтению",
    saveBlacklistTitle: "В чёрный список",
    removeBlacklistTitle: "Убрать из чёрного списка",
    recListActionError: (d) => `Не удалось обновить список: ${d}`,
    fromCache: "Из кэша",
    fresh: "Сгенерировано заново",
    preparingEnrich: "Анализируем ваши книги…",
    preparingRecs: "Подбираем рекомендации…",
    checkingLibrary: "Проверяем вашу библиотеку…",
    wittyPhrases: [
      "Советуемся с книжными оракулами…",
      "Сверяем ваши полки с большим миром…",
      "Готовим персональную подборку…",
      "Обучаем модель понимать «ещё одну главу»…",
      "Отделяем сигнал от шума на полках…",
      "Договариваемся с музами и метаданными…",
    ],
    errorShort: {
      need_sync: "Сначала синхронизируйте библиотеку.",
      need_books: "В библиотеке нужно как минимум две книги.",
      need_enrich: "Сначала выполните быстрый анализ библиотеки.",
      other: "Не удалось загрузить рекомендации.",
    },
  },
  profile: {
    loadFailed: (msg) => `Не удалось загрузить профиль: ${msg}`,
    ready: "Профиль читателя готов",
    prepareFailed: (msg) => `Не удалось подготовить профиль: ${msg}`,
    rebuilt: "Профиль пересобран",
    rebuildFailed: (msg) => `Пересборка не удалась: ${msg}`,
    preparingEnrich: "Анализируем книги…",
    preparingRecs: "Загружаем подборку…",
    title: "Профиль читателя",
    rebuild: "Пересобрать профиль",
    rebuilding: "Пересборка…",
    emptyTitle: "Профиля пока нет.",
    prepareCta: "Подготовить профиль читателя",
    emptySubBefore: "Используется библиотека на вкладке",
    emptySubLink: "«Библиотека»",
    emptySubAfter: ". Нужно как минимум две книги.",
    summary: "Кратко",
    noSummary: "Текста резюме нет.",
    topGenres: "Топ жанров",
    topThemes: "Топ тем",
    moods: "Настроение и темп",
    favoriteAuthors: "Любимые авторы",
    noData: "Нет данных.",
    tagBarAria: (name, pct) => `${name}, ${pct} процентов`,
    authorBarAria: (name, rank, total) =>
      `${name}, место ${rank} из ${total}`,
  },
  settings: {
    title: "Настройки",
    apiKey: "API-ключ",
    baseUrl: "Базовый URL",
    modelOnline: "Онлайн модель",
    modelOffline: "Оффлайн модель",
    presets: "Провайдеры",
    testConnection: "Проверить подключение",
    testing: "Проверка…",
    testSuccess: "Подключение успешно!",
    testFailed: (msg) => `Ошибка подключения: ${msg}`,
    save: "Сохранить",
    saving: "Сохранение…",
    saved: "Настройки сохранены",
    saveFailed: (msg) => `Не удалось сохранить: ${msg}`,
    showKey: "Показать ключ",
    hideKey: "Скрыть ключ",
  },
};

const en: Messages = {
  nav: {
    brand: "My Bookshelf AI",
    library: "Library",
    recommendations: "Recommendations",
    profile: "Profile",
    settings: "Settings",
    ariaMainNav: "Main navigation",
  },
  library: {
    title: "Library",
    search: "Search",
    searchTitle: "Search (Ctrl+O)",
    import_: "Import",
    importing: "Importing…",
    importAria: "Import .md files into library",
    importSuccess: (total, w) => `Imported ${total} ${w}`,
    importFailed: (d) => `Import failed: ${d}`,
    empty: "No books yet.",
    importMd: "Import .md files",
    getRecommendations: "Get recommendations",
    addBook: "Add book",
    addBookAria: "Add a book to the library",
    addBookDialogAria: "Add book",
    addBookTitleLabel: "Title",
    addBookAuthorLabel: "Author",
    addBookRatingLabel: "Rating",
    addBookRatingNone: "No rating",
    addBookNotesLabel: "Notes",
    addBookNotesPlaceholder: "Optional…",
    addBookSubmit: "Add",
    addBookSaving: "Adding…",
    addBookSuccess: "Book added",
    addBookFailed: (d) => `Could not add book: ${d}`,
    addBookEmptyField: "Enter title and author.",
    sortAria: "Book list order",
    sortDefault: "Library order",
    sortTitle: "Alphabetical",
    sortRating: "By rating",
    sortAdded: "Date added",
    plannedListShort: "To read",
    blacklistListShort: "Blocked",
    plannedListOpenAria: "Books marked to read",
    blacklistListOpenAria: "Books hidden from recommendations",
    plannedListTitle: "To read",
    blacklistTitle: "Blocked list",
    plannedListDialogAria: "Reading list from recommendations",
    blacklistListDialogAria: "Blocked recommendations",
    readingListEmpty: "Nothing here yet.",
    readingListLoading: "Loading…",
    removeFromListAria: (title) => `Remove “${title}” from list`,
    readingListLoadError: (d) => `Could not load list: ${d}`,
  },
  search: {
    aria: "Search books",
    placeholder: "Search by title or author…",
    found: (n, w) =>
      n === 1 ? `1 ${w} found` : `${n} ${w} found`,
    noResults: "No books match your search.",
  },
  pagination: {
    aria: "Pagination",
    prev: "Previous",
    next: "Next",
    pageWord: "Page",
    ofWord: "of",
  },
  bookCard: {
    openAria: (title, author) => `Open "${title}" by ${author}`,
    ratingAria: (rating) => `Rating: ${rating} out of 5`,
  },
  bookPanel: {
    loadFailed: "Failed to load book details",
    saved: "Saved",
    saveFailed: "Save failed",
    saveConflict:
      "A book with this title and author already exists. Change the details or merge entries manually.",
    fieldTitle: "Title",
    fieldAuthor: "Author",
    ratingLabel: "Rating",
    clearRating: "No rating",
    ratingValueAria: (n) => `Rating ${n} out of 5`,
    deleted: "Book deleted",
    deleteFailed: "Delete failed",
    dialogAria: (title) => `Book: ${title}`,
    dialogFallbackAria: "Book details",
    closeAria: "Close panel",
    notes: "Notes",
    edit: "Edit",
    cancel: "Cancel",
    saving: "Saving…",
    save: "Save",
    emptyNotes: "No notes yet. Click Edit to add some.",
    confirmDelete: "Delete this book?",
    delete: "Delete",
    deleteBook: "Delete book",
  },
  rec: {
    title: "Recommendations",
    load: "Load",
    wait: "Working…",
    refresh: "Refresh",
    blockedEmpty: "Your library is empty here.",
    syncLibrary: "Sync library",
    blockedMoreBooks: "Add one more book, then sync again.",
    openLibrary: "Open library",
    blockedEnrich:
      "One step: analyze your books, then load picks.",
    enrichCta: "Enrich and show picks",
    details: "Details",
    empty: "No recommendations returned.",
    match: "Match",
    matchAria: (pct) => `Match score ${pct} percent`,
    savePlannedTitle: "Save to reading list",
    removePlannedTitle: "Remove from reading list",
    saveBlacklistTitle: "Hide from recommendations",
    removeBlacklistTitle: "Remove from blocked list",
    recListActionError: (d) => `Could not update list: ${d}`,
    fromCache: "Served from cache",
    fresh: "Freshly generated",
    preparingEnrich: "Analyzing your books…",
    preparingRecs: "Fetching recommendations…",
    checkingLibrary: "Checking your library…",
    wittyPhrases: [
      "Consulting the bookshelf oracles…",
      "Cross-referencing your shelves with the wider world…",
      "Assembling a personal shortlist…",
      "Teaching the model what \u201cone more chapter\u201d means…",
      "Separating signal from shelf noise…",
      "Negotiating with muses and metadata…",
    ],
    errorShort: {
      need_sync: "Sync your library first.",
      need_books: "You need at least two books in your library.",
      need_enrich: "Run a quick analysis on your library.",
      other: "Could not load recommendations.",
    },
  },
  profile: {
    loadFailed: (msg) => `Could not load profile: ${msg}`,
    ready: "Reader profile ready",
    prepareFailed: (msg) => `Could not prepare profile: ${msg}`,
    rebuilt: "Profile rebuilt",
    rebuildFailed: (msg) => `Rebuild failed: ${msg}`,
    preparingEnrich: "Analyzing books…",
    preparingRecs: "Loading picks…",
    title: "Reader profile",
    rebuild: "Rebuild profile",
    rebuilding: "Rebuilding…",
    emptyTitle: "No profile yet.",
    prepareCta: "Prepare reader profile",
    emptySubBefore: "Uses your library on the",
    emptySubLink: "Library",
    emptySubAfter: "tab. You need at least two books.",
    summary: "Summary",
    noSummary: "No summary text.",
    topGenres: "Top genres",
    topThemes: "Top themes",
    moods: "Moods & pace",
    favoriteAuthors: "Favorite authors",
    noData: "No data.",
    tagBarAria: (name, pct) => `${name}, ${pct} percent`,
    authorBarAria: (name, rank, total) =>
      `${name}, rank ${rank} of ${total}`,
  },
  settings: {
    title: "Settings",
    apiKey: "API Key",
    baseUrl: "Base URL",
    modelOnline: "Online model",
    modelOffline: "Offline model",
    presets: "Providers",
    testConnection: "Test connection",
    testing: "Testing…",
    testSuccess: "Connection successful!",
    testFailed: (msg) => `Connection failed: ${msg}`,
    save: "Save",
    saving: "Saving…",
    saved: "Settings saved",
    saveFailed: (msg) => `Save failed: ${msg}`,
    showKey: "Show key",
    hideKey: "Hide key",
  },
};

export const messagesByLocale: Record<Locale, Messages> = {
  ru,
  en,
};
