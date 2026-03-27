"""All user-facing copy for ru/en. Keys are stable; values are translated."""

from __future__ import annotations

# fmt: off
RU: dict[str, str] = {
    "btn_start": "🌿 Начать",
    "btn_about": "ℹ️ О сервисе",
    "btn_donate": "💚 Поддержать",
    "btn_admin": "🛠 Управление",
    "btn_admin_restart": "♻️ Перезапустить",
    "btn_feedback": "✉️ Обратная связь",
    "reply_kb_placeholder": "Выбери, что тебе нужно сейчас",
    "menu_main_hint": "Выбери, с чего хочешь начать.",
    "cmd_start": "Запустить бота",
    "cmd_menu": "Открыть главное меню",
    "cmd_about": "О сервисе",
    "cmd_feedback": "Обратная связь",
    "cmd_donate": "Поддержать проект",
    "cmd_admin": "Админ-аналитика",
    "generic_error": "Что-то пошло не так. Попробуй ещё раз.",
    "empty_fallback": "…",
    "period_today": "Сегодня",
    "period_yesterday": "Вчера",
    "period_7d": "7 дней",
    "period_30d": "30 дней",
    "state_anxious": "🌫️ Тревожно",
    "state_tired": "😴 Нужен отдых",
    "state_overwhelmed": "🌀 Всё навалилось",
    "state_low_energy": "⚡ Мало сил",
    "state_cant_sleep": "🌙 Хочу уснуть",
    "state_need_inspiration": "🎨 Нужен свежий взгляд",
    "preview_anxious": "Мысли крутятся, внутри напряжение и трудно выдохнуть.",
    "preview_tired": "Хочется лечь, замедлиться и хоть немного восстановиться.",
    "preview_overwhelmed": "Слишком много всего сразу: шум, задачи, сообщения или мысли.",
    "preview_low_energy": "Сил мало и трудно включиться даже в первый маленький шаг.",
    "preview_cant_sleep": "Тело устало, а сон не приходит или мысли не отпускают.",
    "preview_need_inspiration": "Хочется ожить, сдвинуться с места и снова почувствовать интерес.",
    "state_preview_heading": "Если не знаешь, что выбрать",
    "rating_1": "🙂 Слабо",
    "rating_2": "😐 Немного",
    "rating_3": "😕 Заметно",
    "rating_4": "😣 Сильно",
    "rating_5": "🚨 Очень тяжело",
    "feedback_nutrition": "🥗 Еда и питание",
    "feedback_activity": "🏃 Движение",
    "feedback_mental": "🧠 Спокойствие и внимание",
    "feedback_biohacking": "⚙️ Сон и повседневные привычки",
    "kb_nav_home": "🏠 В меню",
    "kb_proto_next": "→ Следующий шаг",
    "kb_proto_finish_home": "🏠 Завершить и в меню",
    "kb_donate_humanos": "💚 Поддержать HumanOS",
    "kb_share_friend": "🤝 Поделиться с другом",
    "kb_about_how": "📖 Как это работает",
    "kb_about_back_section": "⬅️ Назад к разделу",
    "kb_period_today": "📅 Сегодня",
    "kb_period_yesterday": "🌘 Вчера",
    "kb_period_7d": "🗓️ 7 дней",
    "kb_period_30d": "📆 30 дней",
    "kb_admin_refresh": "🔄 Обновить",
    "kb_admin_releases": "🗂 Релизы текстов протоколов",
    "kb_admin_feedback_msgs": "💬 Сообщения обратной связи",
    "kb_admin_recent": "🕘 Последние события",
    "kb_admin_restart_bot": "♻️ Перезапустить бота",
    "kb_feedback_survey": "🧭 Что было бы полезно добавить",
    "kb_feedback_write": "💬 Написать нам",
    "kb_feedback_back": "⬅️ Назад",
    "kb_release_back_analytics": "⬅️ Назад к аналитике",
    "kb_release_activate": "↩️ Сделать этот релиз активным",
    "kb_release_back_list": "⬅️ К списку релизов",
    "start_welcome": (
        "Привет. <b>HumanOS</b> — это короткие практики, которые помогают успокоиться, "
        "собраться или немного восстановиться.\n\n"
        "Здесь не нужно делать всё идеально. Если какой-то шаг тебе не подходит, рядом уже есть более мягкий вариант.\n\n"
        "{previews}"
    ),
    "flow_choose_state_title": "<b>Выбери состояние</b>\n\nПосмотри, что больше всего похоже на твоё состояние сейчас.",
    "flow_rating_fallback": "Выбери оценку по шкале ниже.",
    "flow_share_friend_text": (
        "Мне помогла короткая практика в HumanOS. Попробуй тоже, если хочешь немного успокоиться или собраться."
    ),
    "flow_finish_improved_extra": "Если хочешь, можешь поддержать HumanOS или поделиться им с другом.",
    "flow_end_practice_title": "<b>Конец практики</b>\n\nТеперь ещё раз оцени, <i>насколько сильно это мешает тебе сейчас</i>.\n\n{guide}",
    "flow_invalid_initial_rating": "Выбери число от 1 до 5: насколько сильно это мешает тебе сейчас.",
    "flow_invalid_final_rating": "Оцени ещё раз по той же шкале: 1 — почти не мешает, 5 — очень тяжело.",
    "callback_bad_value": "Неверное значение",
    "about_intro": (
        "<b>HumanOS</b> — это короткие практики на те моменты, когда хочется успокоиться, "
        "собраться, отдохнуть или мягко вернуться в себя.\n\n"
        "Практики занимают всего несколько минут и не требуют подготовки. "
        "Если какой-то шаг тебе не подходит, почти всегда рядом уже есть более мягкий вариант.\n\n"
        "Иногда в конце будет простой шаг для поддержки: вода, что-то тёплое, короткая пауза или маленький перекус. Это всегда по желанию.\n\n"
        "HumanOS не заменяет врача. Если тебе плохо уже давно, становится хуже или есть риск для себя и других, лучше искать живую помощь."
    ),
    "about_how": (
        "<b>Как это работает</b>\n\n"
        "1. Нажми «Начать».\n"
        "2. Выбери состояние, которое больше всего похоже на твоё сейчас.\n"
        "3. Оцени, насколько сильно оно мешает: до практики и после неё.\n"
        "4. Пройди шаги по порядку в своём темпе.\n"
        "5. Если что-то не подходит, выбери более мягкий вариант из карточки.\n"
        "6. В конце иногда будет короткий шаг для поддержки. Он не обязателен.\n"
        "7. Если сервис помог, можно поддержать проект или поделиться им с другом."
    ),
    "donate_card": (
        "<b>Поддержать HumanOS</b>\n\n"
        "Если сервис оказался полезным, можно открыть страницу поддержки и самому выбрать сумму."
    ),
    "feedback_root": (
        "<b>Обратная связь</b>\n\n"
        "Здесь можно быстро показать, что тебе было бы полезно дальше, или просто написать нам пару слов."
    ),
    "feedback_root_edit": (
        "<b>Обратная связь</b>\n\n"
        "Выбери, что тебе сейчас удобнее: короткий опрос или обычное сообщение."
    ),
    "feedback_survey_title": (
        "<b>Что было бы особенно полезно дальше?</b>\n\n"
        "Можно выбрать несколько пунктов по очереди."
    ),
    "feedback_write_prompt": (
        "<b>Напиши сообщение</b>\n\n"
        "Можно задать вопрос, описать проблему, предложить идею или просто поделиться впечатлением.\n\n"
        "Просто отправь следующим сообщением текст."
    ),
    "feedback_thanks_saved": "Спасибо. Мы сохранили сообщение и прочитаем его.",
    "feedback_thanks_topic": "Спасибо. Отметил: <b>{label}</b>.",
    "menu_main_title": "Главное меню",
    "nav_home_body": "Ты снова в <b>главном меню</b>. Когда захочешь, нажми «Начать».",
    "about_close_body": "Если захочешь вернуться, раздел «О сервисе» всегда ждёт тебя в меню.",
    "admin_only": "Этот раздел открыт только для администратора.",
    "restart_scheduled": "♻️ Перезапускаю бота. Обычно это занимает несколько секунд.",
    "release_activate_done": (
        "✅ Активен релиз <b>{version}</b>. "
        "Перезапускаю бота — через несколько секунд пользователи получат тексты из этого снимка."
    ),
    "release_not_found": "Релиз не найден",
    "analytics_title": "Аналитика HumanOS",
    "analytics_period_label": "Период",
    "analytics_hint_internal_only": (
        "<i>Сейчас в логе за период есть только действия администраторов или служебных аккаунтов — "
        "они специально не входят в блок «обычные пользователи». Смотри второй блок ниже.</i>\n\n"
    ),
    "analytics_product_block": (
        "<b>Обычные пользователи</b> (без админов и служебных)\n"
        "Событий за период: <b>{p_total}</b>\n"
        "Стартов: <b>{starts}</b>\n"
        "Выборов состояния: <b>{state_sel}</b>\n"
        "Протоколов начато: <b>{started}</b>\n"
        "Протоколов завершено: <b>{completed}</b>\n"
        "Улучшений: <b>{improved}</b>\n"
        "Показов поддержки: <b>{don_shown}</b>\n"
        "Переходов к поддержке: <b>{don_click}</b>\n\n"
        "<b>Возвраты</b> <i>(локальное время сервера; по последним записям в логе, до ~50k строк)</i>\n"
        "Уникальных активных: <b>{active}</b>\n"
        "Вернулись (уже были в логе до начала периода): <b>{returning}</b>\n"
        "Впервые попали в лог в этом периоде: <b>{newu}</b>\n"
        "Активны ≥2 разных дня в периоде: <b>{multiday}</b>\n"
        "Повторно нажали «Начать» (≥2 раза): <b>{repeat_start}</b> чел.\n\n"
        "<b>Типы приложений</b>\n"
        "{p_apps}\n\n"
        "<b>Популярные состояния</b>\n"
        "{p_states}\n\n"
        "<b>Пожелания по доработкам</b>\n"
        "{p_feedback}\n"
        "Свободных сообщений: <b>{fb_msg}</b>"
    ),
    "analytics_internal_block": (
        "<b>Админы и служебные</b> (для отладки, не смешиваются с пользователями)\n"
        "Событий за период: <b>{i_total}</b>\n"
        "Стартов: <b>{istart}</b> | "
        "протоколов: <b>{istartp}</b> / <b>{icompl}</b> | "
        "поддержка показ/клик: <b>{idsh}</b> / <b>{idcl}</b>\n"
        "Ретеншн: активных <b>{iact}</b>, вернулись <b>{iret}</b>, "
        "≥2 дня <b>{imulti}</b>\n\n"
        "<b>Типы приложений</b>\n"
        "{i_apps}\n\n"
        "<b>Состояния</b>\n"
        "{i_states}\n\n"
        "<b>Пожелания</b>\n"
        "{i_feedback}"
    ),
    "analytics_segment_empty": "• пока нет данных",
    "analytics_recent_title": "Последние события",
    "analytics_recent_empty": "Пока пусто.",
    "analytics_recent_no_payload": "без payload",
    "analytics_feedback_title": "Сообщения обратной связи",
    "incident_active": (
        "🔴 <b>Статус</b>: есть активная проблема\n"
        "Последняя причина: {reason}\n"
        "Когда замечено: {when}\n"
        "Автоперезапусков: <b>{restarts}</b>"
    ),
    "incident_ok": (
        "🟢 <b>Статус</b>: бот работает штатно\n"
        "Последнее восстановление: {resolved}\n"
        "Автоперезапусков: <b>{restarts}</b>"
    ),
    "release_archive_empty": (
        "<b>Релизы текстов</b>\n\n"
        "Снимков пока нет. Добавьте JSON в <code>data/protocol_releases/releases/</code> "
        "и перечислите id в <code>registry.json</code>."
    ),
    "release_archive_intro": (
        "<b>Релизы текстов протоколов</b>\n\n"
        "Каждый релиз — отдельный JSON со всеми текстами практик. "
        "<b>Активный</b> загружается при старте бота. "
        "Выбор другого релиза в карточке включает его и <b>перезапускает</b> сервис.\n\n"
    ),
    "release_active_line": "<b>Сейчас активен</b>\n{version} — {title}\n\n",
    "release_list_heading": "<b>Все снимки</b> (новые выше)",
    "release_status_active": "активен",
    "release_status_archive": "архив",
    "release_journal_title": "<b>Журнал</b> (последние события)",
    "release_journal_note": (
        "<i>Действия ниже переведены для чтения; в файле "
        "<code>data/runtime/release_events.jsonl</code> остаются исходные коды.</i>"
    ),
    "release_actor_system": "система",
    "release_actor_id": "id {actor}",
    "release_action_bootstrap": "первая запись / инициализация",
    "release_action_activate": "смена активного релиза",
    "release_detail_not_found": "<b>Релиз не найден</b>",
    "release_detail_protocols": "<b>Состав протоколов</b> ({count})\n{lines}",
    "release_detail_protocols_empty": "<b>Состав протоколов</b>\n<i>не удалось прочитать из JSON</i>",
    "release_detail_notes_heading": "<b>Суть изменений</b> (поле notes, для людей)\n{notes}",
    "release_detail_notes_empty": "<i>В JSON нет массива notes или он пустой.</i>",
    "release_detail_status_active": "✅ активен — бот отдаёт пользователям тексты из этого файла",
    "release_detail_status_archive": "📁 архив — можно снова сделать активным кнопкой ниже",
    "release_detail_card": (
        "<b>Карточка релиза</b>\n\n"
        "<b>ID файла</b>: <code>{rid}</code>\n"
        "<b>Версия</b>: {version}\n"
        "<b>Статус</b>: {status}\n"
        "<b>Метка времени в JSON</b>: {created}\n"
        "<b>Заголовок</b> (поле title): {title}\n\n"
        "{proto}\n\n"
        "{notes_block}"
    ),
    "dash": "—",
    "no_name": "Без имени",
    "unknown": "unknown",
    "feedback_forward_survey_title": "Новый ответ в опросе",
    "feedback_forward_survey_body": "Выбранный пункт: <b>{label}</b>",
    "feedback_forward_free_title": "Новая обратная связь",
    "feedback_forward_admin_template": (
        "<b>{title}</b>\n\n"
        "User ID: <code>{user_id}</code>\n"
        "Username: {username}\n"
        "Имя: {full_name}\n\n"
        "{body}"
    ),
    "prefs_unknown_topic": "Неизвестный вариант опроса.",
    "prefs_feedback_empty": "Напиши хотя бы пару слов, чтобы мы поняли запрос.",
    "prefs_save_failed": "Не получилось сохранить выбор.",
    "prefs_message_failed": "Не получилось сохранить сообщение.",
    "callback_saved": "Сохранил",
    "callback_write_ok": "Можно писать",
    "callback_nav_home": "Возвращаю в меню",
    "callback_refresh": "Обновляю",
    "callback_show_events": "Показываю события",
    "callback_show_fb": "Показываю сообщения",
    "callback_open_releases": "Открываю релизы",
    "callback_release_card": "Карточка релиза",
    "callback_switch_release": "Переключаю релиз",
    "callback_no_rights": "Недостаточно прав",
    "callback_restarting": "Перезапускаю",
    "period_ok": "Ок",
    "err_rating_range": "Введите число от {min} до {max}.",
    "err_need_start_first": "Сначала нужна первая оценка. Нажми «Начать».",
    "err_unknown_state": "Неизвестный вариант. Выберите кнопку из списка.",
    "select_state_prompt": (
        "Сначала оцени, <b>насколько сильно это мешает тебе прямо сейчас</b>.\n\n"
        "<b>{rmin}</b> — почти не мешает. <b>{rmax}</b> — очень тяжело.\n\n"
        "{guide}\n\n"
        "Выбери кнопку ниже. Если так проще, можно просто отправить число."
    ),
    "finish_header": "✅ <b>Практика завершена</b>",
    "finish_scale_hint": "<i>Чем меньше число, тем меньше состояние мешает.</i>",
    "finish_guide_improved_1": (
        "⏳ <b>Сколько это может держаться</b>\n"
        "После такой короткой практики облегчение часто держится <b>от нескольких минут до пары часов</b>. "
        "Иногда заметный сдвиг приходит не сразу, а через 5-15 минут."
    ),
    "finish_guide_improved_2": (
        "🧩 <b>Как сохранить это подольше</b>\n"
        "• не врывайся сразу обратно в шум и дела\n"
        "• сделай пару глотков воды и дай себе 3-5 спокойных минут\n"
        "• если практика помогла, позже можно повторить 1-2 самых комфортных шага\n"
        "• по возможности убери лишний шум, уведомления и спешку"
    ),
    "finish_guide_calm_next": (
        "⏳ <b>Что дальше</b>\n"
        "Сейчас состояние почти не мешает. Обычно такой эффект держится дольше, если не перегружать себя сразу после практики."
    ),
    "finish_guide_flat_1": (
        "⏳ <b>Если пока почти без изменений</b>\n"
        "Это не значит, что практика была зря. Иногда заметный сдвиг приходит не сразу, а через <b>10-20 минут</b>, "
        "особенно если после неё немного посидеть спокойно."
    ),
    "finish_guide_flat_2": (
        "🧩 <b>Что можно сделать дальше</b>\n"
        "• не ругай себя за то, что не отпустило сразу\n"
        "• позже можно вернуться к одному самому комфортному шагу\n"
        "• часто помогает вода, пауза без экрана или короткая спокойная прогулка\n"
        "• если стало хуже, на сегодня лучше остановиться и выбрать самый мягкий вариант"
    ),
    "finish_summary_line": "До практики: <b>{initial}</b> из {mx}. Сейчас: <b>{final_rating}</b> из {mx}.",
    "finish_better": "Сейчас стало легче. Ты уже сделал важную вещь: остановился и дал себе несколько минут.",
    "finish_same": "Оценка не изменилась. Такое бывает. Зато теперь чуть понятнее, что тебе подходит, а что нет.",
    "finish_worse": "Если стало тяжелее, на сегодня достаточно. Сделай паузу и, если нужно, попроси живой помощи.",
    "next_no_protocol": "Практика ещё не началась. Нажми «Начать».",
    "next_need_final": "Переходите к финальной оценке.",
    "next_missing_step": "Шаг не найден.",
    "start_proto_need_state": "Сначала выбери состояние через кнопку «Начать».",
    "start_proto_empty": "Протокол недоступен, попробуйте позже.",
    "start_proto_missing_step": "Шаг протокола не найден.",
    "main_problem": (
        "<b>HumanOS</b>: заметил проблему в обработчике.\n"
        "<pre>{exc}</pre>\n"
        "Проверь логи и состояние сервиса."
    ),
    "main_resolved": "<b>HumanOS</b>: сервис снова в норме после инцидента.",
    "admin_error_handler": (
        "<b>Ошибка в обработчике</b>\n"
        "<pre>{exc}</pre>"
    ),
    "bootstrap_fail": "<b>HumanOS bootstrap</b> не удался:\n<pre>{exc}</pre>",
    "main_incident_problem": (
        "🚨 <b>HumanOS: обнаружена проблема</b>\n\n"
        "<b>Причина</b>: {reason}\n"
        "<b>Что дальше</b>: бот попробует восстановиться автоматически примерно через {restart_delay} сек."
    ),
    "main_incident_resolved": (
        "✅ <b>HumanOS: работа восстановлена</b>\n\n"
        "Бот снова запущен и отвечает на обновления."
    ),
    "main_incident_resolved_suffix": "\n<b>Последняя причина</b>: {reason}",
    "admin_error_alert": "⚠️ <b>HumanOS: ошибка в обработчике</b>\n\n<code>{title}</code>\n<code>{detail}</code>",
}

EN: dict[str, str] = {
    "btn_start": "🌿 Start",
    "btn_about": "ℹ️ About",
    "btn_donate": "💚 Support",
    "btn_admin": "🛠 Admin",
    "btn_admin_restart": "♻️ Restart bot",
    "btn_feedback": "✉️ Feedback",
    "reply_kb_placeholder": "Choose what you need right now",
    "menu_main_hint": "Choose where to begin.",
    "cmd_start": "Start the bot",
    "cmd_menu": "Open main menu",
    "cmd_about": "About the service",
    "cmd_feedback": "Feedback",
    "cmd_donate": "Support the project",
    "cmd_admin": "Admin analytics",
    "generic_error": "Something went wrong. Please try again.",
    "empty_fallback": "…",
    "period_today": "Today",
    "period_yesterday": "Yesterday",
    "period_7d": "7 days",
    "period_30d": "30 days",
    "state_anxious": "🌫️ Anxious",
    "state_tired": "😴 Need rest",
    "state_overwhelmed": "🌀 Overwhelmed",
    "state_low_energy": "⚡ Low energy",
    "state_cant_sleep": "🌙 Can’t sleep",
    "state_need_inspiration": "🎨 Need a fresh view",
    "preview_anxious": "Thoughts keep spinning, tension inside, hard to exhale.",
    "preview_tired": "You want to lie down, slow down, recover a little.",
    "preview_overwhelmed": "Too much at once: noise, tasks, messages, or thoughts.",
    "preview_low_energy": "Little strength; hard to start even a tiny step.",
    "preview_cant_sleep": "Body is tired but sleep won’t come or thoughts won’t let go.",
    "preview_need_inspiration": "You want to come alive, move, and feel interest again.",
    "state_preview_heading": "If you’re unsure what to pick",
    "rating_1": "🙂 Mild",
    "rating_2": "😐 A little",
    "rating_3": "😕 Noticeable",
    "rating_4": "😣 Strong",
    "rating_5": "🚨 Very heavy",
    "feedback_nutrition": "🥗 Food & nutrition",
    "feedback_activity": "🏃 Movement",
    "feedback_mental": "🧠 Calm & attention",
    "feedback_biohacking": "⚙️ Sleep & daily habits",
    "kb_nav_home": "🏠 Main menu",
    "kb_proto_next": "→ Next step",
    "kb_proto_finish_home": "🏠 Finish & go to menu",
    "kb_donate_humanos": "💚 Support HumanOS",
    "kb_share_friend": "🤝 Share with a friend",
    "kb_about_how": "📖 How it works",
    "kb_about_back_section": "⬅️ Back to section",
    "kb_period_today": "📅 Today",
    "kb_period_yesterday": "🌘 Yesterday",
    "kb_period_7d": "🗓️ 7 days",
    "kb_period_30d": "📆 30 days",
    "kb_admin_refresh": "🔄 Refresh",
    "kb_admin_releases": "🗂 Protocol text releases",
    "kb_admin_feedback_msgs": "💬 Feedback messages",
    "kb_admin_recent": "🕘 Recent events",
    "kb_admin_restart_bot": "♻️ Restart bot",
    "kb_feedback_survey": "🧭 What would help next",
    "kb_feedback_write": "💬 Write to us",
    "kb_feedback_back": "⬅️ Back",
    "kb_release_back_analytics": "⬅️ Back to analytics",
    "kb_release_activate": "↩️ Make this release active",
    "kb_release_back_list": "⬅️ Back to list",
    "start_welcome": (
        "Hi. <b>HumanOS</b> offers short practices to calm down, "
        "focus, or recover a little.\n\n"
        "You don’t have to do everything perfectly. If a step doesn’t fit, a gentler option is usually nearby.\n\n"
        "{previews}"
    ),
    "flow_choose_state_title": "<b>Pick a state</b>\n\nChoose what feels closest to how you feel right now.",
    "flow_rating_fallback": "Pick a score using the buttons below.",
    "flow_share_friend_text": (
        "A short HumanOS practice helped me. Try it if you want to calm down or refocus."
    ),
    "flow_finish_improved_extra": "If you like, you can support HumanOS or share it with a friend.",
    "flow_end_practice_title": "<b>End of practice</b>\n\nRate again <i>how much this is bothering you right now</i>.\n\n{guide}",
    "flow_invalid_initial_rating": "Pick a number from 1 to 5: how much is this bothering you right now?",
    "flow_invalid_final_rating": "Rate again on the same scale: 1 — barely bothers you, 5 — very hard.",
    "callback_bad_value": "Invalid value",
    "about_intro": (
        "<b>HumanOS</b> is short practices for moments when you want to calm down, "
        "focus, rest, or gently come back to yourself.\n\n"
        "Sessions take just a few minutes and need no preparation. "
        "If a step doesn’t fit, there’s almost always a softer option nearby.\n\n"
        "Sometimes there’s a simple support step at the end: water, warmth, a short pause, or a small snack. Always optional.\n\n"
        "HumanOS is not a doctor. If you’ve felt bad for a long time, things are getting worse, or there’s risk to you or others, seek real-world help."
    ),
    "about_how": (
        "<b>How it works</b>\n\n"
        "1. Tap <b>Start</b>.\n"
        "2. Pick the state that fits you best right now.\n"
        "3. Rate how much it bothers you — before and after the practice.\n"
        "4. Go through the steps at your own pace.\n"
        "5. If something doesn’t fit, choose a gentler option on the card.\n"
        "6. Sometimes there’s a short support step at the end. It’s optional.\n"
        "7. If the service helped, you can support the project or share it."
    ),
    "donate_card": (
        "<b>Support HumanOS</b>\n\n"
        "If it was useful, you can open the support page and choose an amount."
    ),
    "feedback_root": (
        "<b>Feedback</b>\n\n"
        "Quickly show what would help you next, or write us a few words."
    ),
    "feedback_root_edit": (
        "<b>Feedback</b>\n\n"
        "Choose what’s easier now: a short survey or a free-form message."
    ),
    "feedback_survey_title": (
        "<b>What would be especially useful next?</b>\n\n"
        "You can pick several items one after another."
    ),
    "feedback_write_prompt": (
        "<b>Write a message</b>\n\n"
        "Ask a question, describe a problem, suggest an idea, or share an impression.\n\n"
        "Just send the text in your next message."
    ),
    "feedback_thanks_saved": "Thank you. We’ve saved your message and will read it.",
    "feedback_thanks_topic": "Thanks. Noted: <b>{label}</b>.",
    "menu_main_title": "Main menu",
    "nav_home_body": "You’re back in the <b>main menu</b>. Tap <b>Start</b> whenever you’re ready.",
    "about_close_body": "Whenever you want, <b>About</b> is still in the menu.",
    "admin_only": "This section is only for an administrator.",
    "restart_scheduled": "♻️ Restarting the bot. Usually takes a few seconds.",
    "release_activate_done": (
        "✅ Active release: <b>{version}</b>. "
        "Restarting the bot — in a few seconds users will get texts from this snapshot."
    ),
    "release_not_found": "Release not found",
    "analytics_title": "HumanOS analytics",
    "analytics_period_label": "Period",
    "analytics_hint_internal_only": (
        "<i>The log for this period only has admin or service accounts — "
        "they’re excluded from the “regular users” block below. See the second block.</i>\n\n"
    ),
    "analytics_product_block": (
        "<b>Regular users</b> (excluding admins & service)\n"
        "Events in period: <b>{p_total}</b>\n"
        "Starts: <b>{starts}</b>\n"
        "State picks: <b>{state_sel}</b>\n"
        "Protocols started: <b>{started}</b>\n"
        "Protocols completed: <b>{completed}</b>\n"
        "Improved: <b>{improved}</b>\n"
        "Donation screens: <b>{don_shown}</b>\n"
        "Donation clicks: <b>{don_click}</b>\n\n"
        "<b>Retention</b> <i>(server local time; tail of log, up to ~50k lines)</i>\n"
        "Unique active: <b>{active}</b>\n"
        "Returning (seen before period start): <b>{returning}</b>\n"
        "First seen in log this period: <b>{newu}</b>\n"
        "Active ≥2 calendar days: <b>{multiday}</b>\n"
        "Tapped Start ≥2 times: <b>{repeat_start}</b>\n\n"
        "<b>App types</b>\n"
        "{p_apps}\n\n"
        "<b>Popular states</b>\n"
        "{p_states}\n\n"
        "<b>Feature wishes</b>\n"
        "{p_feedback}\n"
        "Free-form messages: <b>{fb_msg}</b>"
    ),
    "analytics_internal_block": (
        "<b>Admins & service</b> (debug, not mixed with users)\n"
        "Events in period: <b>{i_total}</b>\n"
        "Starts: <b>{istart}</b> | "
        "protocols: <b>{istartp}</b> / <b>{icompl}</b> | "
        "donation show/click: <b>{idsh}</b> / <b>{idcl}</b>\n"
        "Retention: active <b>{iact}</b>, returning <b>{iret}</b>, "
        "≥2 days <b>{imulti}</b>\n\n"
        "<b>App types</b>\n"
        "{i_apps}\n\n"
        "<b>States</b>\n"
        "{i_states}\n\n"
        "<b>Wishes</b>\n"
        "{i_feedback}"
    ),
    "analytics_segment_empty": "• no data yet",
    "analytics_recent_title": "Recent events",
    "analytics_recent_empty": "Nothing yet.",
    "analytics_recent_no_payload": "no payload",
    "analytics_feedback_title": "Feedback messages",
    "incident_active": (
        "🔴 <b>Status</b>: active incident\n"
        "Last reason: {reason}\n"
        "Noticed at: {when}\n"
        "Auto-restarts: <b>{restarts}</b>"
    ),
    "incident_ok": (
        "🟢 <b>Status</b>: operating normally\n"
        "Last recovery: {resolved}\n"
        "Auto-restarts: <b>{restarts}</b>"
    ),
    "release_archive_empty": (
        "<b>Text releases</b>\n\n"
        "No snapshots yet. Add JSON under <code>data/protocol_releases/releases/</code> "
        "and list ids in <code>registry.json</code>."
    ),
    "release_archive_intro": (
        "<b>Protocol text releases</b>\n\n"
        "Each release is one JSON with all practice texts. "
        "The <b>active</b> one loads at bot startup. "
        "Picking another in the card activates it and <b>restarts</b> the service.\n\n"
    ),
    "release_active_line": "<b>Currently active</b>\n{version} — {title}\n\n",
    "release_list_heading": "<b>All snapshots</b> (newest first)",
    "release_status_active": "active",
    "release_status_archive": "archive",
    "release_journal_title": "<b>Journal</b> (latest events)",
    "release_journal_note": (
        "<i>Actions below are translated for reading; "
        "<code>data/runtime/release_events.jsonl</code> keeps raw codes.</i>"
    ),
    "release_actor_system": "system",
    "release_actor_id": "id {actor}",
    "release_action_bootstrap": "first record / bootstrap",
    "release_action_activate": "active release switch",
    "release_detail_not_found": "<b>Release not found</b>",
    "release_detail_protocols": "<b>Protocols</b> ({count})\n{lines}",
    "release_detail_protocols_empty": "<b>Protocols</b>\n<i>Could not read from JSON</i>",
    "release_detail_notes_heading": "<b>What changed</b> (notes field)\n{notes}",
    "release_detail_notes_empty": "<i>No notes array in JSON or it’s empty.</i>",
    "release_detail_status_active": "✅ active — users get texts from this file",
    "release_detail_status_archive": "📁 archive — can be activated with the button below",
    "release_detail_card": (
        "<b>Release card</b>\n\n"
        "<b>File ID</b>: <code>{rid}</code>\n"
        "<b>Version</b>: {version}\n"
        "<b>Status</b>: {status}\n"
        "<b>Timestamp in JSON</b>: {created}\n"
        "<b>Title</b>: {title}\n\n"
        "{proto}\n\n"
        "{notes_block}"
    ),
    "dash": "—",
    "no_name": "No name",
    "unknown": "unknown",
    "feedback_forward_survey_title": "New survey answer",
    "feedback_forward_survey_body": "Selected: <b>{label}</b>",
    "feedback_forward_free_title": "New feedback",
    "feedback_forward_admin_template": (
        "<b>{title}</b>\n\n"
        "User ID: <code>{user_id}</code>\n"
        "Username: {username}\n"
        "Name: {full_name}\n\n"
        "{body}"
    ),
    "prefs_unknown_topic": "Unknown survey option.",
    "prefs_feedback_empty": "Write at least a few words so we understand.",
    "prefs_save_failed": "Couldn’t save the choice.",
    "prefs_message_failed": "Couldn’t save the message.",
    "callback_saved": "Saved",
    "callback_write_ok": "Go ahead",
    "callback_nav_home": "Back to menu",
    "callback_refresh": "Refreshing",
    "callback_show_events": "Showing events",
    "callback_show_fb": "Showing messages",
    "callback_open_releases": "Opening releases",
    "callback_release_card": "Release card",
    "callback_switch_release": "Switching release",
    "callback_no_rights": "Not allowed",
    "callback_restarting": "Restarting",
    "period_ok": "OK",
    "err_rating_range": "Enter a number from {min} to {max}.",
    "err_need_start_first": "Start with the first rating. Tap <b>Start</b>.",
    "err_unknown_state": "Unknown option. Use a button from the list.",
    "select_state_prompt": (
        "First rate <b>how much this is bothering you right now</b>.\n\n"
        "<b>{rmin}</b> — barely bothers you. <b>{rmax}</b> — very hard.\n\n"
        "{guide}\n\n"
        "Use the buttons below, or send a number if that’s easier."
    ),
    "finish_header": "✅ <b>Practice complete</b>",
    "finish_scale_hint": "<i>Lower score means it bothers you less.</i>",
    "finish_guide_improved_1": (
        "⏳ <b>How long it may last</b>\n"
        "After a short practice, relief often lasts <b>from a few minutes to a couple of hours</b>. "
        "Sometimes the shift shows up after 5–15 minutes."
    ),
    "finish_guide_improved_2": (
        "🧩 <b>How to make it stick longer</b>\n"
        "• don’t dive straight back into noise and tasks\n"
        "• drink a little water and give yourself 3–5 calm minutes\n"
        "• if it helped, you can repeat 1–2 comfortable steps later\n"
        "• when you can, reduce noise, notifications, and rushing"
    ),
    "finish_guide_calm_next": (
        "⏳ <b>What’s next</b>\n"
        "Right now it barely gets in the way. The effect usually lasts longer if you don’t overload yourself right after."
    ),
    "finish_guide_flat_1": (
        "⏳ <b>If little has changed yet</b>\n"
        "That doesn’t mean the practice was pointless. A noticeable shift sometimes comes after <b>10–20 minutes</b>, "
        "especially if you sit quietly for a bit."
    ),
    "finish_guide_flat_2": (
        "🧩 <b>What you can do next</b>\n"
        "• don’t blame yourself if it didn’t lift immediately\n"
        "• later you can return to one comfortable step\n"
        "• water, screen-free pause, or a short calm walk often help\n"
        "• if it feels worse, stop for today and pick the gentlest option"
    ),
    "finish_summary_line": "Before: <b>{initial}</b> of {mx}. Now: <b>{final_rating}</b> of {mx}.",
    "finish_better": "It feels lighter now. You already did something important: you paused and gave yourself a few minutes.",
    "finish_same": "The score didn’t change. That happens. Now it’s a bit clearer what fits you and what doesn’t.",
    "finish_worse": "If it feels heavier, that’s enough for today. Pause and, if needed, ask for real-world help.",
    "next_no_protocol": "The practice hasn’t started yet. Tap <b>Start</b>.",
    "next_need_final": "Go to the final rating.",
    "next_missing_step": "Step not found.",
    "start_proto_need_state": "First pick a state with <b>Start</b>.",
    "start_proto_empty": "Protocol unavailable, try again later.",
    "start_proto_missing_step": "Protocol step not found.",
    "main_problem": (
        "<b>HumanOS</b>: handler issue detected.\n"
        "<pre>{exc}</pre>\n"
        "Check logs and service state."
    ),
    "main_resolved": "<b>HumanOS</b>: service is healthy again after the incident.",
    "admin_error_handler": (
        "<b>Handler error</b>\n"
        "<pre>{exc}</pre>"
    ),
    "bootstrap_fail": "<b>HumanOS bootstrap</b> failed:\n<pre>{exc}</pre>",
    "main_incident_problem": (
        "🚨 <b>HumanOS: problem detected</b>\n\n"
        "<b>Reason</b>: {reason}\n"
        "<b>Next</b>: the bot will try to recover automatically in about {restart_delay} s."
    ),
    "main_incident_resolved": (
        "✅ <b>HumanOS: back online</b>\n\n"
        "The bot is running again and processing updates."
    ),
    "main_incident_resolved_suffix": "\n<b>Last reason</b>: {reason}",
    "admin_error_alert": "⚠️ <b>HumanOS: handler error</b>\n\n<code>{title}</code>\n<code>{detail}</code>",
}

MESSAGES: dict[str, dict[str, str]] = {"ru": RU, "en": EN}
STATE_ORDER: tuple[str, ...] = (
    "anxious",
    "tired",
    "overwhelmed",
    "low_energy",
    "cant_sleep",
    "need_inspiration",
)
FEEDBACK_ORDER: tuple[str, ...] = ("nutrition", "activity", "mental", "biohacking")
# fmt: on
