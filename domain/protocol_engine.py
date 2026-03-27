"""Protocol registry and resolution. Pure data + lookup — no transports."""

from __future__ import annotations

from dataclasses import dataclass
import re
from random import choices
from typing import Any, Dict, Mapping

from domain.models import Protocol as StoredProtocol
from domain.models import ProtocolStep as StoredProtocolStep


@dataclass(frozen=True, slots=True)
class ProtocolStep:
    """Один шаг в расширенном словаре ``PROTOCOLS`` (фаза + текст + секунды)."""

    phase: str
    title: str
    body: str
    duration_seconds: int


@dataclass(frozen=True, slots=True)
class Protocol:
    """Описание протокола для ``PROTOCOLS``."""

    state: str
    title: str
    estimated_minutes: int
    steps: tuple[ProtocolStep, ...]


PROTOCOLS: Dict[str, Protocol] = {
    "Нужен отдых": Protocol(
        state="Нужен отдых",
        title="Протокол «Глубокая пауза»",
        estimated_minutes=8,
        steps=(
            ProtocolStep(
                "body",
                "Опора для отдыха",
                "Найди спокойное место. Ляг на спину и устрой тело так, чтобы оно не держалось лишний раз. Если тебе удобно, положи голени на стул или диван, чтобы колени были согнуты. Если хочется, можно и поднять ноги на стену, но только если это правда приятно. Руки положи рядом с телом или на живот. Плечи отпусти. Челюсть не сжимай. Побудь так 2 минуты. Если есть беременность на позднем сроке, сильное давление в голове, глаукома или неприятные ощущения в спине и глазах, лучше лечь на бок с подушкой между коленями или остаться в варианте со стулом.",
                120,
            ),
            ProtocolStep(
                "breath",
                "Тихое дыхание 4-6",
                "Оставайся в удобной позе. Сделай вдох через нос на 4 счёта, потом выдох на 6. Не задерживай дыхание и не выжимай из себя длинный выдох. Если такой ритм не подходит, спокойно перейди на 3 и 4. Продолжай 3 минуты. Если кружится голова или становится неприятно, вернись к обычному дыханию. Здесь важнее мягкость, чем точный счёт.",
                180,
            ),
            ProtocolStep(
                "attention",
                "Замечать, как отпускает тело",
                "Положи одну ладонь на грудь, вторую на живот или просто оставь руки рядом. Заметь три вещи: как лежат плечи, как касается опоры спина, и стал ли живот мягче, чем в начале. Можно тихо сказать себе: «сейчас можно не спешить». Побудь так 2 минуты. Если прикосновение к телу неприятно, просто смотри в одну точку и замечай опору под собой.",
                120,
            ),
            ProtocolStep(
                "adapt",
                "Напиток / поддержка после практики",
                "Этот шаг не обязателен. Если хочешь, выпей тёплой воды или очень слабый напиток без кофеина. Если есть изжога, чувствительный желудок, беременность или просто не хочется ничего лишнего, выбирай обычную тёплую воду. Если сейчас вечер, ничего бодрящего лучше не добавлять. Ещё один хороший вариант: 3 минуты полежать или посидеть без телефона.",
                0,
            ),
        ),
    ),
    "Перегруз": Protocol(
        state="Перегруз",
        title="Протокол «Перегруз»",
        estimated_minutes=8,
        steps=(
            ProtocolStep(
                "body",
                "Собрать тело в одну точку",
                "Сядь на стул или на край кровати. Поставь стопы на пол. Ладони положи на бёдра или обними себя за плечи. На 5-7 секунд слегка надави ладонями на бёдра или мягко сожми себя руками, потом отпусти. Повтори 4-5 раз. Это помогает телу почувствовать границы и чуть снизить внутренний шум. Если касание неприятно, просто сильно упрись стопами в пол на те же 5-7 секунд и потом отпусти.",
                90,
            ),
            ProtocolStep(
                "breath",
                "Спокойный выдох 4-6",
                "Сядь удобно. Сделай вдох через нос на 4 секунды, потом выдох на 6. Если это легко, можно иногда выдыхать чуть дольше, но без усилия. Задержек не нужно. Продолжай 3 минуты. Если длинный счёт не подходит, сократи до 3 и 4. Если дыхание само просит паузу, не мешай ему. Здесь цель — не успеть, а немного приглушить перегруз.",
                210,
            ),
            ProtocolStep(
                "attention",
                "Сузить внимание",
                "Выбери одну спокойную точку перед собой: край стола, угол стены, складку ткани. Смотри только туда 1 минуту. Потом назови про себя 3 звука, которые слышишь, и 3 ощущения в теле, которые замечаешь прямо сейчас. Не нужно искать что-то особенное. Здесь задача — уменьшить количество входящего шума и собрать внимание в более простой картине.",
                120,
            ),
            ProtocolStep(
                "adapt",
                "Напиток / поддержка после практики",
                "Этот шаг по желанию. Выпей немного воды и не бери телефон хотя бы ещё 1-2 минуты. Если тебе подходят травяные напитки, можно выбрать что-то тёплое без кофеина. Если не любишь травы, есть аллергия, беременность, ограничения от врача или просто не хочется лишнего, обычной воды достаточно. После перегруза часто лучше сработает тишина, чем ещё одна стимуляция.",
                0,
            ),
        ),
    ),
    "Нужен заряд": Protocol(
        state="Нужен заряд",
        title="Протокол «Мягкий разгон»",
        estimated_minutes=7,
        steps=(
            ProtocolStep(
                "body",
                "Разбудить тело",
                "Встань прямо и сделай 1 минуту бодрого, но мягкого движения. Лучше всего подойдут шаг на месте, перекаты с пятки на носок, круги плечами и движения руками крест-накрест. Можно пройтись по комнате в хорошем темпе. Если есть беременность, боль в коленях, спине или просто не хочется двигаться активно, выбери более спокойный вариант: шаг на месте и потягивания вверх.",
                40,
            ),
            ProtocolStep(
                "breath",
                "Чёткий ритм 3 на 3",
                "Останься стоя или сядь ровно. Сделай 10-12 дыханий в ритме: вдох на 3 счёта, выдох на 3. Потом один обычный спокойный вдох и выдох. Повтори ещё 2 круга. Дыши чуть собраннее обычного, но без резкости. Если становится некомфортно, просто вернись к обычному дыханию. Это мягче и безопаснее, чем слишком активные дыхательные техники, но всё равно помогает проснуться.",
                120,
            ),
            ProtocolStep(
                "attention",
                "Одна цель на 3 минуты",
                "Сразу после движения выбери одну очень маленькую задачу, которая реально двинет тебя вперёд. Например: открыть документ, написать заголовок, налить воду и сесть за стол, открыть нужную вкладку, включить музыку без слов. Скажи себе: «я делаю только это». Если трудно выбрать, бери самый маленький вариант. Здесь важнее запуск, чем идеальный выбор.",
                120,
            ),
            ProtocolStep(
                "adapt",
                "Напиток / поддержка после практики",
                "Этот шаг не обязателен. Если сейчас первая половина дня и кофеин тебе подходит, можно выбрать маленькую порцию чая или кофе. Если не хочется кофеина или он тебе не подходит, лучше взять воду, яблоко, банан, йогурт или другой простой перекус. Если сейчас вечер, есть беременность, тревога, сердцебиение или чувствительность к кофеину, выбирай вариант без него. Здесь задача — не раскрутить себя слишком сильно, а немного поддержать силы.",
                0,
            ),
        ),
    ),
    "Тревога": Protocol(
        state="Тревога",
        title="Протокол «Тревога»",
        estimated_minutes=6,
        steps=(
            ProtocolStep(
                "body",
                "Опора и ноги",
                "Сядь так, чтобы обе стопы полностью стояли на полу. Слегка прижми их к полу и почувствуй опору под ногами. Плечи опусти вниз. Можно 10-15 секунд мягко потрясти кистями и пальцами, потом положить руки на бёдра. Побудь так 1 минуту. Если сидеть неудобно, можно встать и просто заметить, как ноги держат тебя.",
                60,
            ),
            ProtocolStep(
                "breath",
                "Длинный выдох",
                "Сделай вдох через нос на 3 или 4 счёта, а выдох чуть длиннее — на 5 или 6. Повторяй 2 минуты. Если через нос выдыхать неудобно, выдыхай через губы, будто медленно дуешь на свечу. Если кружится голова, сократи счёт. Здесь не нужно терпеть. Важно только то, чтобы выдох был чуть длиннее и мягче.",
                120,
            ),
            ProtocolStep(
                "attention",
                "5-4-3",
                "Медленно назови про себя 5 вещей, которые видишь. Потом 4 звука вокруг. Потом 3 части тела, которые сейчас хорошо чувствуешь. Если этого много, сократи до 3-2-1. Не нужно делать всё идеально. Смысл в том, чтобы вернуть внимание из тревожных мыслей в то, что есть прямо сейчас.",
                120,
            ),
            ProtocolStep(
                "adapt",
                "Тёплая вода или мягкий напиток",
                "Выпей полстакана тёплой воды маленькими глотками. Если хочется чего-то ещё, подойдёт напиток без кофеина. Если желудок чувствительный, есть тошнота или изжога, ничего кислого не добавляй. Если пить не хочется, просто посиди ещё минуту спокойно или укройся пледом. Этого достаточно.",
                60,
            ),
        ),
    ),
    "Расфокус": Protocol(
        state="Расфокус",
        title="Протокол «Расфокус»",
        estimated_minutes=6,
        steps=(
            ProtocolStep(
                "body",
                "Встать и размять шею",
                "Встань или сядь ровно. Сделай 5 медленных кругов плечами назад. Потом мягко поверни голову вправо и влево, только до приятной точки. Руками шею не тяни. Делай это 1 минуту. Если шея болит, оставь только движение плечами и взгляд вправо-влево. Так тоже подойдёт.",
                60,
            ),
            ProtocolStep(
                "breath",
                "Счёт вдоха",
                "Сядь. Считай только вдохи: первый вдох — «один», следующий — «два» и так до десяти. Потом снова начни с единицы. Если отвлёкся, не ругай себя, просто начни сначала. Делай так 2 минуты.",
                120,
            ),
            ProtocolStep(
                "attention",
                "Одна задача",
                "Выбери одну совсем маленькую задачу на 2 минуты. Например: убрать одну вещь со стола, открыть документ, написать заголовок или налить воду. Делай только её. Не переключайся и не бери в руки телефон. Сейчас этого достаточно.",
                120,
            ),
            ProtocolStep(
                "adapt",
                "Вода и короткая подпитка",
                "Сходи за водой и выпей медленно. Если понимаешь, что дело в голоде, добавь простой перекус: яблоко, банан, кусочек хлеба, йогурт или немного орехов. Если уже поздний вечер, не пытайся взбодриться кофеином. Лучше вода и короткая пауза без экрана.",
                90,
            ),
        ),
    ),
    "Раздражение": Protocol(
        state="Раздражение",
        title="Протокол «Раздражение»",
        estimated_minutes=6,
        steps=(
            ProtocolStep(
                "body",
                "Сжать и отпустить",
                "Сожми кулаки на 5 секунд, потом отпусти и потряси кистями 10 секунд. Повтори 3 раза. Плечи держи опущенными. Челюсть не сжимай. Если кулаки сжимать неприятно, просто сильно прижми ладони друг к другу, а потом расслабь. Выбирай тот вариант, который легче.",
                60,
            ),
            ProtocolStep(
                "breath",
                "Выдох «фу»",
                "Вдохни через нос, а на выдохе тихо протяни «фууу» или просто длинный шипящий звук. Сделай так 10 раз. Звук нужен только для того, чтобы выдох стал длиннее. Если не хочется звучать, делай просто долгий выдох через рот. Это тоже работает.",
                90,
            ),
            ProtocolStep(
                "attention",
                "Холод воды",
                "Умойся прохладной водой или подержи руки под прохладной струёй 30-40 секунд. Потом вытри руки и посмотри вдаль: в окно, на дальнюю стену или в угол комнаты. Если холод неприятен или только сильнее напрягает, используй воду комнатной температуры. Главное, чтобы тебе было терпимо.",
                90,
            ),
            ProtocolStep(
                "adapt",
                "Маленький перекус",
                "Если раздражение усиливается от голода, съешь что-то простое: яблоко, хлеб, банан, йогурт или немного орехов. Если хочется пить, подойдёт вода или тёплый некрепкий чай. Если есть беременность, чувствительный желудок или уже поздний вечер, выбирай самый простой и привычный вариант. Без экспериментов.",
                120,
            ),
        ),
    ),
    "Не могу уснуть": Protocol(
        state="Не могу уснуть",
        title="Протокол «Тихий переход ко сну»",
        estimated_minutes=8,
        steps=(
            ProtocolStep(
                "body",
                "Устроиться удобнее",
                "Ляг или сядь так, чтобы телу было правда удобно. Можно подложить подушку под колени, под поясницу или чуть приподнять голову, если есть изжога, насморк или беременность. Если лежать пока некомфортно, сядь на край кровати и слегка округли спину. Побудь так 2 минуты. Здесь не нужно «засыпать правильно». Сначала важно дать телу сигнал, что можно сбавить темп.",
                120,
            ),
            ProtocolStep(
                "breath",
                "Длинный выдох перед сном",
                "Сделай вдох через нос на 3 или 4 счёта, а выдох на 5 или 6. Дыши спокойно, без задержек. Продолжай 3 минуты. Если длинный счёт раздражает или не подходит, сократи его до 2 и 4. Если нос заложен, можно делать тихий длинный выдох через рот. Если само слово «счёт» только злит, просто делай выдох немного длиннее вдоха. Этого достаточно.",
                180,
            ),
            ProtocolStep(
                "attention",
                "Снять лишнее напряжение",
                "Медленно пройди вниманием по телу сверху вниз: глаза, челюсть, язык, плечи, живот, руки, ноги. На каждом участке тихо говори себе: «можно отпустить». Не старайся расслабить всё сразу. Достаточно заметить, где тело всё ещё держится. Если мысли снова уносят, просто мягко вернись к следующей части тела.",
                120,
            ),
            ProtocolStep(
                "adapt",
                "Тёплая вода и тишина",
                "Этот шаг по желанию. Сделай пару маленьких глотков воды, только если не боишься потом снова проснуться в туалет. Свет лучше оставить приглушённым, а телефон больше не брать в руки. Если мысли крутятся по кругу, можно коротко выписать их на бумагу и отложить до утра. Если сильная бессонница держится много дней подряд или ночная тревога становится тяжёлой, лучше обсудить это с врачом.",
                60,
            ),
        ),
    ),
    "Нужно вдохновение": Protocol(
        state="Нужно вдохновение",
        title="Протокол «Искра»",
        estimated_minutes=7,
        steps=(
            ProtocolStep(
                "body",
                "Сменить позу и двинуться",
                "Встань и сделай 1 минуту простого движения: шагай на месте, потянись вверх, покрути плечами, пройдись по комнате. Можно сделать несколько движений крест-накрест: правой рукой к левому боку, левой рукой к правому. Не нужно делать это энергично. Цель в том, чтобы слегка сдвинуть тело из застывшего состояния. Если стоять неудобно, сделай всё сидя.",
                60,
            ),
            ProtocolStep(
                "breath",
                "Сбросить внутренний шум",
                "Сделай 6-8 спокойных циклов дыхания: вдох на 4 счёта, выдох на 6. Не торопись. На выдохе можно тихо подумать: «освобождаю место». Если счёт мешает, просто сделай выдох чуть длиннее вдоха. Если хочется зевнуть или потянуться, не мешай этому. Смысл шага в том, чтобы стало меньше внутренней суеты и больше свободного внимания.",
                120,
            ),
            ProtocolStep(
                "attention",
                "Одна живая идея",
                "Теперь не пытайся придумать всё сразу. Ответь себе на вопрос: «Что сейчас цепляет меня хоть немного?» Это может быть слово, образ, цвет, музыка, тема, человек или одна маленькая задача. Запиши 3 коротких варианта без оценки и без отбора. Потом выбери тот, где больше всего жизни прямо сейчас. Не ищи идею мечты. Здесь достаточно поймать даже слабую искру.",
                180,
            ),
            ProtocolStep(
                "adapt",
                "Поддержать интерес",
                "Этот шаг по желанию. Выпей воды или тёплого чая. Потом выбери один совсем маленький следующий шаг на 3-5 минут: открыть заметку, собрать референсы, написать первую строку, набросать три слова, сделать один эскиз. Если не хочется ничего творческого, можно просто сохранить одну идею на потом. Не требуй от себя вдохновения на весь день. Сейчас достаточно начать движение в нужную сторону.",
                60,
            ),
        ),
    ),
}


# Ключи состояний бота (shared.constants) → ключи в PROTOCOLS (русские названия)
_STATE_KEY_TO_RU: dict[str, str] = {
    "anxious": "Тревога",
    "tired": "Нужен отдых",
    "overwhelmed": "Перегруз",
    "low_energy": "Нужен заряд",
    "cant_sleep": "Не могу уснуть",
    "need_inspiration": "Нужно вдохновение",
}

_PHASE_LABELS: dict[str, tuple[str, str]] = {
    "body": ("🧍", "Тело"),
    "breath": ("🌬️", "Дыхание"),
    "attention": ("🎯", "Фокус"),
    "adapt": ("🍵", "Поддержка"),
}


def _paragraphize(text: str) -> str:
    """Break long prose into short mobile-friendly paragraphs."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    if not sentences:
        return text
    blocks: list[str] = []
    current: list[str] = []
    for sentence in sentences:
        current.append(sentence)
        if len(current) == 2:
            blocks.append(" ".join(current))
            current = []
    if current:
        blocks.append(" ".join(current))
    return "\n\n".join(blocks)


def _split_step_body(text: str) -> tuple[str, str | None]:
    """Split prose into main instructions and fallback/options block."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    if not sentences:
        return text.strip(), None
    main: list[str] = []
    options: list[str] = []
    for sentence in sentences:
        if sentence.startswith("Если") or sentence.startswith("Этот шаг"):
            options.append(sentence)
        else:
            main.append(sentence)
    main_text = " ".join(main).strip() or text.strip()
    options_text = " ".join(options).strip() or None
    return main_text, options_text


def _step_from_body(
    *,
    protocol_id: str,
    phase: str,
    title: str,
    body: str,
    duration_seconds: int,
    release_id: str,
    release_version: str,
    variant_id: str,
) -> StoredProtocolStep:
    how_to, alternatives = _split_step_body(body)
    return StoredProtocolStep(
        id=f"{protocol_id}:{phase}",
        title=title,
        body=body,
        phase=phase,
        duration_seconds=duration_seconds,
        how_to=how_to,
        alternatives=alternatives,
        release_id=release_id,
        release_version=release_version,
        variant_id=variant_id,
    )


def _step_from_structured(
    *,
    protocol_id: str,
    step_data: Mapping[str, Any],
    release_id: str,
    release_version: str,
    variant_id: str,
) -> StoredProtocolStep:
    phase = str(step_data.get("phase") or "")
    title = str(step_data.get("title") or "")
    how_to = str(step_data.get("how_to") or "")
    alternatives = str(step_data.get("alternatives") or "").strip() or None
    goal = str(step_data.get("goal") or "").strip() or None
    notes = str(step_data.get("notes") or "").strip() or None
    body_parts = [part for part in (how_to, alternatives, goal, notes) if part]
    return StoredProtocolStep(
        id=f"{protocol_id}:{phase}",
        title=title,
        body="\n\n".join(body_parts),
        phase=phase,
        duration_seconds=int(step_data.get("duration_seconds") or 0),
        how_to=how_to,
        alternatives=alternatives,
        goal=goal,
        notes=notes,
        release_id=release_id,
        release_version=release_version,
        variant_id=variant_id,
    )


def _rich_protocol_to_stored(
    spec: Protocol,
    protocol_id: str,
    *,
    release_id: str = "builtin",
    release_version: str = "builtin",
    variant_id: str = "main",
) -> StoredProtocol:
    """Превращает запись из PROTOCOLS в модель, которой пользуется ProtocolEngine и бот."""
    steps = tuple(
        _step_from_body(
            protocol_id=protocol_id,
            phase=s.phase,
            title=s.title,
            body=s.body,
            duration_seconds=s.duration_seconds,
            release_id=release_id,
            release_version=release_version,
            variant_id=variant_id,
        )
        for s in spec.steps
    )
    return StoredProtocol(
        id=protocol_id,
        name=spec.title,
        description=f"Ориентир по времени: около {spec.estimated_minutes} минут.",
        steps=steps,
        release_id=release_id,
        release_version=release_version,
        variant_id=variant_id,
    )


def build_protocol_engine_from_release(release_data: Mapping[str, Any]) -> ProtocolEngine:
    release_id = str(release_data.get("release_id") or "unknown")
    release_version = str(release_data.get("version") or release_id)
    protocols: dict[str, dict[str, StoredProtocol]] = {}
    default_variant_ids: dict[str, str] = {}
    variant_weights: dict[str, dict[str, int]] = {}
    raw_protocols = dict(release_data.get("protocols") or {})
    for protocol_id, protocol_spec in raw_protocols.items():
        variants: dict[str, StoredProtocol] = {}
        weights: dict[str, int] = {}
        variant_entries = list(protocol_spec.get("variants") or ())
        if not variant_entries:
            raise ValueError(f"Protocol {protocol_id} in release {release_id} has no variants")
        for raw_variant in variant_entries:
            variant_id = str(raw_variant.get("id") or "main")
            steps = tuple(
                _step_from_structured(
                    protocol_id=str(protocol_id),
                    step_data=step_data,
                    release_id=release_id,
                    release_version=release_version,
                    variant_id=variant_id,
                )
                for step_data in raw_variant.get("steps") or ()
            )
            variants[variant_id] = StoredProtocol(
                id=str(protocol_id),
                name=str(protocol_spec.get("title") or protocol_id),
                description=f"Ориентир по времени: около {int(protocol_spec.get('estimated_minutes') or 0)} минут.",
                steps=steps,
                release_id=release_id,
                release_version=release_version,
                variant_id=variant_id,
            )
            weights[variant_id] = max(1, int(raw_variant.get("weight") or 1))
        protocols[str(protocol_id)] = variants
        default_variant_ids[str(protocol_id)] = next(iter(variants))
        variant_weights[str(protocol_id)] = weights

    state_to_protocol = {key: key for key in _STATE_KEY_TO_RU}
    return ProtocolEngine(
        protocols=protocols,
        state_to_protocol=state_to_protocol,
        default_protocol_id="anxious",
        default_variant_ids=default_variant_ids,
        variant_weights=variant_weights,
        release_id=release_id,
        release_version=release_version,
        release_title=str(release_data.get("title") or release_id),
        release_notes=tuple(str(item) for item in release_data.get("notes") or ()),
    )


def build_default_protocol_engine() -> ProtocolEngine:
    """
    Собирает движок из словаря PROTOCOLS (единый источник текстов протоколов).

    Ключи состояний в сессии — англ. (`anxious`, `tired`, …), как в кнопках бота.
    """
    protocols: dict[str, dict[str, StoredProtocol]] = {}
    default_variant_ids: dict[str, str] = {}
    variant_weights: dict[str, dict[str, int]] = {}
    for state_key, ru_key in _STATE_KEY_TO_RU.items():
        rich = PROTOCOLS.get(ru_key)
        if rich is None:
            raise KeyError(f"PROTOCOLS is missing entry for state {state_key!r} → {ru_key!r}")
        protocols[state_key] = {"main": _rich_protocol_to_stored(rich, state_key)}
        default_variant_ids[state_key] = "main"
        variant_weights[state_key] = {"main": 1}

    state_to_protocol = {key: key for key in _STATE_KEY_TO_RU}
    return ProtocolEngine(
        protocols=protocols,
        state_to_protocol=state_to_protocol,
        default_protocol_id="anxious",
        default_variant_ids=default_variant_ids,
        variant_weights=variant_weights,
        release_id="builtin",
        release_version="builtin",
        release_title="Built-in release",
        release_notes=(),
    )


def _format_duration(seconds: int) -> str | None:
    if seconds <= 0:
        return None
    if seconds < 60:
        return f"≈ {seconds} сек"
    minutes = seconds // 60
    rem = seconds % 60
    if rem == 0:
        return f"≈ {minutes} мин"
    return f"≈ {minutes} мин {rem} сек"


class ProtocolEngine:
    """
    Holds protocols as data and maps abstract user states to protocol ids.

    Extend by registering more protocols and editing ``state_to_protocol``.
    """

    def __init__(
        self,
        protocols: Mapping[str, Mapping[str, StoredProtocol]],
        state_to_protocol: Mapping[str, str],
        default_protocol_id: str,
        default_variant_ids: Mapping[str, str],
        variant_weights: Mapping[str, Mapping[str, int]],
        release_id: str,
        release_version: str,
        release_title: str,
        release_notes: tuple[str, ...],
    ) -> None:
        self._protocols = {pid: dict(variants) for pid, variants in protocols.items()}
        self._state_to_protocol = dict(state_to_protocol)
        self._default_protocol_id = default_protocol_id
        self._default_variant_ids = dict(default_variant_ids)
        self._variant_weights = {
            pid: {variant_id: int(weight) for variant_id, weight in weights.items()}
            for pid, weights in variant_weights.items()
        }
        self._release_id = release_id
        self._release_version = release_version
        self._release_title = release_title
        self._release_notes = tuple(release_notes)
        if default_protocol_id not in self._protocols:
            raise ValueError(f"default_protocol_id {default_protocol_id!r} not in protocols")
        for pid in self._state_to_protocol.values():
            if pid not in self._protocols:
                raise ValueError(f"protocol {pid!r} referenced but not registered")

    def resolve_protocol_id(self, state_key: str) -> str:
        """Pick protocol for emotional/physical state key."""
        return self._state_to_protocol.get(state_key, self._default_protocol_id)

    def current_release(self) -> dict[str, Any]:
        return {
            "release_id": self._release_id,
            "release_version": self._release_version,
            "release_title": self._release_title,
            "release_notes": self._release_notes,
        }

    def choose_variant(self, protocol_id: str) -> str:
        weights = self._variant_weights.get(protocol_id) or {}
        if not weights:
            return self._default_variant_ids.get(protocol_id, "main")
        variant_ids = list(weights.keys())
        selected = choices(variant_ids, weights=[weights[item] for item in variant_ids], k=1)[0]
        return str(selected)

    def get_protocol(self, protocol_id: str, *, variant_id: str | None = None) -> StoredProtocol | None:
        variants = self._protocols.get(protocol_id)
        if not variants:
            return None
        resolved_variant = variant_id or self._default_variant_ids.get(protocol_id)
        return variants.get(str(resolved_variant)) or variants.get(self._default_variant_ids.get(protocol_id, "main"))

    def get_step(self, protocol_id: str, step_index: int, *, variant_id: str | None = None) -> StoredProtocolStep | None:
        proto = self.get_protocol(protocol_id, variant_id=variant_id)
        if not proto or step_index < 0 or step_index >= len(proto.steps):
            return None
        return proto.steps[step_index]

    def step_count(self, protocol_id: str, *, variant_id: str | None = None) -> int:
        proto = self.get_protocol(protocol_id, variant_id=variant_id)
        return len(proto.steps) if proto else 0

    def format_step_message(self, step: StoredProtocolStep, *, index: int, total: int) -> str:
        """Human-readable step text (could be swapped for i18n)."""
        phase = step.phase or (step.id.rsplit(":", 1)[-1] if ":" in step.id else "")
        emoji, label = _PHASE_LABELS.get(phase, ("✨", "Шаг"))
        main_text = step.how_to or _split_step_body(step.body)[0]
        options_text = step.alternatives or _split_step_body(step.body)[1]
        duration = _format_duration(step.duration_seconds)
        parts = [
            f"{emoji} <b>Шаг {index + 1}. {label}: {step.title}</b>",
            f"📍 <b>Этап</b>\nШаг {index + 1} из {total}",
        ]
        if duration:
            parts.append(f"⏱️ <b>Время</b>\n{duration}")
        parts.append(f"▶️ <b>Как делать</b>\n{_paragraphize(main_text)}")
        if options_text:
            parts.append(f"🛟 <b>Если нужен другой вариант</b>\n{_paragraphize(options_text)}")
        if step.goal:
            parts.append(f"🎯 <b>Зачем это</b>\n{_paragraphize(step.goal)}")
        if step.notes:
            parts.append(f"📝 <b>Важно</b>\n{_paragraphize(step.notes)}")
        return "\n\n".join(parts)
