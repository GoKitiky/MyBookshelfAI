"""Pre-seed demo books, enrichments, reader profile, and recommendations for empty libraries."""

from __future__ import annotations

import logging

from app.locale import AppLocale
from app.models import Book, EnrichedBook, ReaderProfile
from app.services.cache import CacheNamespace, make_key, set_cache
from app.services.library_db import get_all_books, upsert_book
from app.services.profile import ProfileBuilder
from app.services.recommendation_scoring import apply_match_scores_to_recommendation_dicts
from app.services.settings_db import set_setting

logger = logging.getLogger(__name__)

_NUM_DEMO_RECS = 5

_DEMO_BOOKS_RU: list[dict[str, str | int]] = [
    {
        "title": "1984",
        "author": "Джордж Оруэлл",
        "rating": 5,
        "review": (
            "Пугающе актуальная антиутопия. Книга, которую перечитываешь и каждый раз "
            "находишь новые параллели с реальностью."
        ),
    },
    {
        "title": "Мастер и Маргарита",
        "author": "Михаил Булгаков",
        "rating": 5,
        "review": (
            "Роман-загадка, в котором дьявол оказывается самым честным персонажем. "
            "Сатира, любовь и мистика переплетены виртуозно."
        ),
    },
    {
        "title": "Дюна",
        "author": "Фрэнк Герберт",
        "rating": 4,
        "review": (
            "Масштабный мир с уникальной экологией и политикой. "
            "Читается как эпос, а не как фантастика."
        ),
    },
    {
        "title": "Братья Карамазовы",
        "author": "Фёдор Достоевский",
        "rating": 1,
        "review": (
            "Тяжеловесный и затянутый роман. Философские отступления утомляют, "
            "а персонажи раздражают больше, чем вызывают сочувствие."
        ),
    },
    {
        "title": "Автостопом по галактике",
        "author": "Дуглас Адамс",
        "rating": 3,
        "review": (
            "Забавная, но местами слишком абсурдная. Юмор на любителя, "
            "хотя «42» — это, конечно, гениально."
        ),
    },
    {
        "title": "Солярис",
        "author": "Станислав Лем",
        "rating": 5,
        "review": (
            "Философская фантастика в чистом виде. Лем заставляет задуматься "
            "о границах человеческого познания."
        ),
    },
    {
        "title": "Гордость и предубеждение",
        "author": "Джейн Остен",
        "rating": 3,
        "review": (
            "Классика, но несколько предсказуемая. Остин мастерски описывает нравы, "
            "но темп повествования медленный."
        ),
    },
    {
        "title": "Пикник на обочине",
        "author": "Аркадий и Борис Стругацкие",
        "rating": 4,
        "review": (
            "Атмосферная и тревожная повесть. Зона — один из самых запоминающихся "
            "образов в мировой фантастике."
        ),
    },
    {
        "title": "Великий Гэтсби",
        "author": "Фрэнсис Скотт Фицджеральд",
        "rating": 2,
        "review": (
            "Красивый язык, но пустые персонажи. История о богатстве и разочаровании "
            "не вызвала отклика."
        ),
    },
    {
        "title": "Мы",
        "author": "Евгений Замятин",
        "rating": 5,
        "review": (
            "Первоисточник всех антиутопий. Поразительно, как точно Замятин предсказал "
            "механизмы тоталитаризма."
        ),
    },
]

_DEMO_BOOKS_EN: list[dict[str, str | int]] = [
    {
        "title": "1984",
        "author": "George Orwell",
        "rating": 5,
        "review": (
            "A chillingly relevant dystopia. Every reread surfaces new parallels "
            "with the world around us."
        ),
    },
    {
        "title": "The Master and Margarita",
        "author": "Mikhail Bulgakov",
        "rating": 5,
        "review": (
            "A puzzle-box novel where the devil may be the most honest character. "
            "Satire, love, and mysticism woven together with virtuosity."
        ),
    },
    {
        "title": "Dune",
        "author": "Frank Herbert",
        "rating": 4,
        "review": (
            "A vast world with a singular ecology and politics. "
            "It reads like an epic, not ordinary science fiction."
        ),
    },
    {
        "title": "The Brothers Karamazov",
        "author": "Fyodor Dostoevsky",
        "rating": 1,
        "review": (
            "Heavy and drawn-out. The philosophical digressions tire, "
            "and the characters annoy more than they move you."
        ),
    },
    {
        "title": "The Hitchhiker's Guide to the Galaxy",
        "author": "Douglas Adams",
        "rating": 3,
        "review": (
            "Funny, but sometimes too absurd for its own good. The humor is an acquired taste—"
            "though “42” remains brilliant."
        ),
    },
    {
        "title": "Solaris",
        "author": "Stanisław Lem",
        "rating": 5,
        "review": (
            "Philosophical science fiction at its purest. Lem pushes you to question "
            "the limits of human understanding."
        ),
    },
    {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "rating": 3,
        "review": (
            "A classic, if somewhat predictable. Austen nails manners and society, "
            "but the pace is slow."
        ),
    },
    {
        "title": "Roadside Picnic",
        "author": "Arkady and Boris Strugatsky",
        "rating": 4,
        "review": (
            "Atmospheric and uneasy. The Zone is one of the most memorable images "
            "in world science fiction."
        ),
    },
    {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "rating": 2,
        "review": (
            "Beautiful prose, hollow people. The story of wealth and disillusionment "
            "never quite landed for me."
        ),
    },
    {
        "title": "We",
        "author": "Yevgeny Zamyatin",
        "rating": 5,
        "review": (
            "The ur-text of modern dystopia. Zamyatin foresaw the machinery of "
            "totalitarianism with uncanny precision."
        ),
    },
]

_DEMO_ENRICHMENTS_RU: list[dict[str, str | list[str]]] = [
    {
        "genres": ["антиутопия", "социальная фантастика"],
        "themes": ["тоталитаризм", "свобода личности", "пропаганда"],
        "mood": "мрачное",
        "complexity": "moderate",
        "similar_authors": ["Aldous Huxley", "Ray Bradbury"],
    },
    {
        "genres": ["магический реализм", "сатира"],
        "themes": ["добро и зло", "любовь", "творчество", "вера"],
        "mood": "мистическое",
        "complexity": "complex",
        "similar_authors": ["Nikolai Gogol", "Gabriel García Márquez"],
    },
    {
        "genres": ["научная фантастика", "эпос"],
        "themes": ["власть", "экология", "религия", "судьба"],
        "mood": "эпическое",
        "complexity": "complex",
        "similar_authors": ["Isaac Asimov", "Ursula K. Le Guin"],
    },
    {
        "genres": ["философский роман", "драма"],
        "themes": ["вера и безверие", "отцы и дети", "нравственный выбор"],
        "mood": "тяжёлое",
        "complexity": "complex",
        "similar_authors": ["Leo Tolstoy", "Franz Kafka"],
    },
    {
        "genres": ["юмористическая фантастика", "сатира"],
        "themes": ["смысл жизни", "абсурд", "бюрократия"],
        "mood": "ироничное",
        "complexity": "light",
        "similar_authors": ["Terry Pratchett", "Kurt Vonnegut"],
    },
    {
        "genres": ["научная фантастика", "философская проза"],
        "themes": ["познание", "одиночество", "контакт с неизвестным"],
        "mood": "философское",
        "complexity": "complex",
        "similar_authors": ["Philip K. Dick", "Arthur C. Clarke"],
    },
    {
        "genres": ["роман нравов", "романтика"],
        "themes": ["социальные нормы", "предрассудки", "любовь"],
        "mood": "лёгкое",
        "complexity": "light",
        "similar_authors": ["Charlotte Brontë", "Elizabeth Gaskell"],
    },
    {
        "genres": ["научная фантастика", "философская проза"],
        "themes": ["инопланетный контакт", "запретное знание", "человечность"],
        "mood": "тревожное",
        "complexity": "moderate",
        "similar_authors": ["Stanisław Lem", "Philip K. Dick"],
    },
    {
        "genres": ["классическая литература", "драма"],
        "themes": ["американская мечта", "богатство", "разочарование"],
        "mood": "меланхоличное",
        "complexity": "moderate",
        "similar_authors": ["Ernest Hemingway", "John Steinbeck"],
    },
    {
        "genres": ["антиутопия", "научная фантастика"],
        "themes": ["свобода", "индивидуальность", "тоталитаризм"],
        "mood": "мрачное",
        "complexity": "moderate",
        "similar_authors": ["George Orwell", "Aldous Huxley"],
    },
]

_DEMO_ENRICHMENTS_EN: list[dict[str, str | list[str]]] = [
    {
        "genres": ["dystopian fiction", "social science fiction"],
        "themes": ["totalitarianism", "personal freedom", "propaganda"],
        "mood": "bleak",
        "complexity": "moderate",
        "similar_authors": ["Aldous Huxley", "Ray Bradbury"],
    },
    {
        "genres": ["magical realism", "satire"],
        "themes": ["good and evil", "love", "creativity", "faith"],
        "mood": "mystical",
        "complexity": "complex",
        "similar_authors": ["Nikolai Gogol", "Gabriel García Márquez"],
    },
    {
        "genres": ["science fiction", "space opera"],
        "themes": ["power", "ecology", "religion", "fate"],
        "mood": "epic",
        "complexity": "complex",
        "similar_authors": ["Isaac Asimov", "Ursula K. Le Guin"],
    },
    {
        "genres": ["philosophical novel", "drama"],
        "themes": ["faith and doubt", "fathers and sons", "moral choice"],
        "mood": "weighty",
        "complexity": "complex",
        "similar_authors": ["Leo Tolstoy", "Franz Kafka"],
    },
    {
        "genres": ["humorous science fiction", "satire"],
        "themes": ["meaning of life", "absurdity", "bureaucracy"],
        "mood": "ironic",
        "complexity": "light",
        "similar_authors": ["Terry Pratchett", "Kurt Vonnegut"],
    },
    {
        "genres": ["science fiction", "philosophical fiction"],
        "themes": ["knowledge", "loneliness", "contact with the unknown"],
        "mood": "contemplative",
        "complexity": "complex",
        "similar_authors": ["Philip K. Dick", "Arthur C. Clarke"],
    },
    {
        "genres": ["novel of manners", "romance"],
        "themes": ["social norms", "prejudice", "love"],
        "mood": "light",
        "complexity": "light",
        "similar_authors": ["Charlotte Brontë", "Elizabeth Gaskell"],
    },
    {
        "genres": ["science fiction", "philosophical fiction"],
        "themes": ["alien contact", "forbidden knowledge", "humanity"],
        "mood": "uneasy",
        "complexity": "moderate",
        "similar_authors": ["Stanisław Lem", "Philip K. Dick"],
    },
    {
        "genres": ["classic literature", "drama"],
        "themes": ["the American dream", "wealth", "disillusionment"],
        "mood": "melancholic",
        "complexity": "moderate",
        "similar_authors": ["Ernest Hemingway", "John Steinbeck"],
    },
    {
        "genres": ["dystopian fiction", "science fiction"],
        "themes": ["freedom", "individuality", "totalitarianism"],
        "mood": "bleak",
        "complexity": "moderate",
        "similar_authors": ["George Orwell", "Aldous Huxley"],
    },
]

_DEMO_PROFILE_SUMMARY_RU = (
    "Вы — вдумчивый читатель с выраженным вкусом к интеллектуальной прозе. "
    "Ваша библиотека тяготеет к антиутопиям и философской фантастике — "
    "произведениям, которые исследуют границы свободы, познания и человечности. "
    "Вам близки мрачные, но глубокие истории, где автор ставит неудобные вопросы, "
    "а не даёт простые ответы. При этом вы цените и сатиру, и магический реализм — "
    "жанры, которые позволяют взглянуть на действительность через призму абсурда."
)

_DEMO_PROFILE_SUMMARY_EN = (
    "You are a thoughtful reader with a strong appetite for literary fiction. "
    "Your shelf leans toward dystopia and philosophical science fiction—work that probes "
    "freedom, knowledge, and what it means to be human. You gravitate to dark, "
    "substantial stories that ask uncomfortable questions instead of offering easy answers. "
    "You also value satire and magical realism—genres that refract reality through absurdity."
)

_DEMO_RECOMMENDATIONS_RU: list[dict[str, str | list[str]]] = [
    {
        "title": "451 градус по Фаренгейту",
        "author": "Рэй Брэдбери",
        "genres": ["антиутопия", "научная фантастика"],
        "themes": ["цензура", "свобода мысли", "технологии"],
        "reasoning": (
            "Роман рисует мир, где книги сжигают, а мышление считается преступлением. "
            "Брэдбери создаёт пронзительную метафору интеллектуальной стерильности, "
            "написанную поэтическим языком."
        ),
    },
    {
        "title": "Собачье сердце",
        "author": "Михаил Булгаков",
        "genres": ["сатира", "фантастика"],
        "themes": ["эксперимент", "человечность", "социальная критика"],
        "reasoning": (
            "Повесть о профессоре, превратившем бродячего пса в человека, обнажает "
            "абсурд революционных преобразований. Гротеск и острый юмор сочетаются "
            "с горькой философской подоплёкой."
        ),
    },
    {
        "title": "Нейромант",
        "author": "Уильям Гибсон",
        "genres": ["киберпанк", "научная фантастика"],
        "themes": ["искусственный интеллект", "виртуальная реальность", "отчуждение"],
        "reasoning": (
            "Дебютный роман Гибсона заложил фундамент жанра киберпанк. Неоновые "
            "трущобы, хакеры и разумные сети сплетаются в нуарную историю о свободе "
            "в цифровую эпоху."
        ),
    },
    {
        "title": "Обитаемый остров",
        "author": "Аркадий и Борис Стругацкие",
        "genres": ["научная фантастика", "социальная фантастика"],
        "themes": ["тоталитаризм", "манипуляция сознанием", "сопротивление"],
        "reasoning": (
            "Земной разведчик попадает на планету, жители которой контролируются "
            "психотронными излучателями. Стругацкие мастерски выстраивают мир, "
            "где правда оказывается сложнее лозунгов."
        ),
    },
    {
        "title": "О дивный новый мир",
        "author": "Олдос Хаксли",
        "genres": ["антиутопия", "социальная фантастика"],
        "themes": ["потребительство", "свобода выбора", "контроль"],
        "reasoning": (
            "Хаксли изображает общество, где счастье стало обязательным, "
            "а индивидуальность — угрозой стабильности. Произведение остаётся "
            "тревожно актуальным спустя почти столетие после написания."
        ),
    },
]

_DEMO_RECOMMENDATIONS_EN: list[dict[str, str | list[str]]] = [
    {
        "title": "Fahrenheit 451",
        "author": "Ray Bradbury",
        "genres": ["dystopian fiction", "science fiction"],
        "themes": ["censorship", "intellectual freedom", "technology"],
        "reasoning": (
            "Bradbury imagines a world where books are burned and thinking is a crime. "
            "It is a piercing metaphor for intellectual sterility, told in lush, poetic prose."
        ),
    },
    {
        "title": "Heart of a Dog",
        "author": "Mikhail Bulgakov",
        "genres": ["satire", "fantasy"],
        "themes": ["experiment", "humanity", "social critique"],
        "reasoning": (
            "A professor turns a stray dog into a man, exposing the absurdity of social "
            "engineering. Grotesque humor sits on top of a bitter philosophical core."
        ),
    },
    {
        "title": "Neuromancer",
        "author": "William Gibson",
        "genres": ["cyberpunk", "science fiction"],
        "themes": ["artificial intelligence", "virtual reality", "alienation"],
        "reasoning": (
            "Gibson’s debut codified cyberpunk: neon slums, hackers, and intelligent networks "
            "in a noir story about agency in a digital age."
        ),
    },
    {
        "title": "Hard to Be a God",
        "author": "Arkady and Boris Strugatsky",
        "genres": ["science fiction", "social science fiction"],
        "themes": ["totalitarianism", "manipulation", "resistance"],
        "reasoning": (
            "An Earth observer lands on a planet stuck in a cruel middle age. The Strugatskys "
            "build a world where truth is messier than propaganda."
        ),
    },
    {
        "title": "Brave New World",
        "author": "Aldous Huxley",
        "genres": ["dystopian fiction", "social science fiction"],
        "themes": ["consumerism", "free will", "social control"],
        "reasoning": (
            "Huxley depicts a society where happiness is mandatory and individuality threatens "
            "stability. It still feels unnervingly current almost a century later."
        ),
    },
]

_DEMO_BY_LOCALE: dict[
    AppLocale,
    tuple[
        list[dict[str, str | int]],
        list[dict[str, str | list[str]]],
        str,
        list[dict[str, str | list[str]]],
    ],
] = {
    "ru": (
        _DEMO_BOOKS_RU,
        _DEMO_ENRICHMENTS_RU,
        _DEMO_PROFILE_SUMMARY_RU,
        _DEMO_RECOMMENDATIONS_RU,
    ),
    "en": (
        _DEMO_BOOKS_EN,
        _DEMO_ENRICHMENTS_EN,
        _DEMO_PROFILE_SUMMARY_EN,
        _DEMO_RECOMMENDATIONS_EN,
    ),
}

SETTING_DEMO_LIBRARY = "demo_library"


async def ensure_demo_library_seeded(locale: AppLocale) -> None:
    """If the library is empty, seed demo content for the requested UI locale."""
    if get_all_books():
        return
    await seed_demo_library(locale)


async def seed_demo_library(locale: AppLocale) -> None:
    """Populate an empty library with demo books, enrichments, profile, and recommendations."""
    if get_all_books():
        return

    demo_books, demo_enrichments, profile_summary, demo_recs = _DEMO_BY_LOCALE[locale]

    logger.info("Library is empty — seeding demo data (locale=%s)", locale)

    books: list[Book] = []
    # Reversed so prepending each new row keeps _DEMO_BOOKS visual order.
    for raw, enrichment_data in zip(
        reversed(demo_books), reversed(demo_enrichments), strict=True
    ):
        title = str(raw["title"])
        author = str(raw["author"])
        rating = int(raw["rating"])
        review = str(raw["review"])

        upsert_book(
            title=title,
            author=author,
            rating=rating,
            review=review,
        )
        book = Book(
            title=title,
            author=author,
            rating=rating,
            review=review,
        )
        books.append(book)

        enriched = EnrichedBook(book=book, **enrichment_data)
        cache_key = make_key(locale, book.title, book.author)
        await set_cache(
            CacheNamespace.ENRICHED_BOOKS,
            cache_key,
            enriched.model_dump(),
        )

    enriched_books = [
        EnrichedBook(book=b, **e)
        for b, e in zip(books, demo_enrichments, strict=True)
    ]
    profile: ReaderProfile = ProfileBuilder._aggregate(enriched_books)
    profile.summary = profile_summary

    book_ids = sorted(b.get_id() for b in books)
    profile_cache_key = make_key(locale, *book_ids)
    await set_cache(
        CacheNamespace.READER_PROFILE,
        profile_cache_key,
        profile.model_dump(),
    )

    rec_dicts = apply_match_scores_to_recommendation_dicts(
        [dict(r) for r in demo_recs],
        profile,
    )
    rec_cache_key = make_key(locale, "recs", profile.model_dump(), _NUM_DEMO_RECS)
    await set_cache(
        CacheNamespace.RECOMMENDATIONS,
        rec_cache_key,
        rec_dicts,
    )

    set_setting(SETTING_DEMO_LIBRARY, "true")
    logger.info(
        "Demo library seeded: %d books, profile, and recommendations (locale=%s)",
        len(books),
        locale,
    )
