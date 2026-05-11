import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    filters, ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler
)

from modules.log.log import log
from modules.constants import (
    WORK_FORMAT_MAP, EMPLOYMENT_MAP, EXPERIENCE_MAP, REGION_MAP
)
from modules.parser.parser import create_rss_request_url, parse_rss_url_to_dict, render_rss_params_template, \
    parse_rss_feed, parse_vacancy, render_job_card_template
from modules.db.db import add_rss_subscription, list_user_rss_subscriptions, fetch_all_rss_dict


TELEGRAM_API_TOKEN = ""
VACANCIES_PARSE_LIMIT =  2


# Состояния диалога
(SEARCH_TEXT, REGION, WORK_FORMAT, EMPLOYMENT_FORM, EXPERIENCE) = range(5)


app = ApplicationBuilder().token(TELEGRAM_API_TOKEN).build()


def build_keyboard(options_map: dict, skip_callback: str = "SKIP") -> InlineKeyboardMarkup:
    """Строит клавиатуру из словаря {callback_data: label} + кнопка Пропустить"""
    buttons = [
        [InlineKeyboardButton(label, callback_data=data)]
        for data, label in options_map.items()
    ]
    buttons.append([InlineKeyboardButton("⏭ Пропустить", callback_data=skip_callback)])
    return InlineKeyboardMarkup(buttons)


async def unexpected_text_on_keyboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Пожалуйста, используйте кнопки для выбора или нажмите 'Пропустить'."
    )


async def start_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        text=f"Привет, {update.message.from_user.first_name}! "
             f"Можем начинать, для получения справочной информации введи /help"
    )


async def help_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = "\n".join([
        "📜 Доступные команды:",
        "/start – Начать взаимодействие с ботом",
        "/help – Показать это сообщение",
        "/subscribe – Подписаться на рассылку вакансий с заданными параметрами",
        "/unsubscribe – Отказаться от рассылки по определённым параметрам",
        "/reset – Отказаться от всех действующих рассылок"
    ])
    await update.message.reply_text(text=help_text)


async def show_subscriptions_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subscriptions = list_user_rss_subscriptions(user_id)

    message = f""

    for _, _, rss_url in subscriptions:
        params = parse_rss_url_to_dict(rss_url)
        message += render_rss_params_template("templates/rss_params_message.html", params)
        message += "\n"

    await update.message.reply_text(
        f"📝 <b>Ваши подписки:</b>\n{message}",
        parse_mode='HTML'
    )


async def send_vacancies_info():
    users_rss = fetch_all_rss_dict()

    for user_id, subscriptions in users_rss.items():
        for subscription in subscriptions:
            rss_url = subscription.get("url")
            try:
                log.info(f"Load RSS {rss_url}...")
                rss_items = parse_rss_feed(rss_url)
                log.info(f"Find {len(rss_items)} items...")

                results = []
                for i, item in enumerate(rss_items[:VACANCIES_PARSE_LIMIT]):
                    log.info(f"[{i + 1}/{VACANCIES_PARSE_LIMIT}] Parse: {item['title']}")

                    vacancy_data = parse_vacancy(item['link'])
                    if vacancy_data:
                        results.append(vacancy_data)
                        log.info(f"Successfully parsed...")
                    else:
                        log.info(f"Failed to parse...")

                    # Пауза между запросами
                    await asyncio.sleep(1)

                # По каждой вакансии отправить уведомление пользователю
                for vac in results:
                    try:
                        job_card = render_job_card_template(
                            template_path="./templates/jobs.html",
                            vacancy=vac
                        )

                        await app.bot.send_message(
                            chat_id=user_id,
                            text=job_card,
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        log.error(f"Failed to send vacancy to user {user_id}: {e}")

            except Exception as e:
                log.error(f"Failed to process subscription {rss_url} for user {user_id}: {e}")


async def unsubscribe_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


async def reset_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


# ==================== ConversationHandler: /subscribe ====================

async def subscribe_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 1: запрашиваем поисковый запрос"""
    await update.message.reply_text(
        "🔍 Введите поисковый запрос (например, «Python разработчик» или «DevOps»):"
    )
    return SEARCH_TEXT


async def search_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем поисковый запрос и переходим к выбору региона"""

    # Сохранить текст запроса для поиска вакансий
    context.user_data["search_text"] = update.message.text

    # Отправить пользователю клавиатуру для выбора региона поиска вакансий
    await update.message.reply_text(
        "📍 Выберите регион поиска:",
        reply_markup=build_keyboard(REGION_MAP)
    )
    return REGION


async def region_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем регион, переходим к формату работы"""

    # Ожидать выбор пользователем региона поиска вакансий из списка, предоставленного в search_text_received
    query = update.callback_query
    await query.answer()

    # Извлечь из ответа регион для поиска вакансий, если пользователь не пропустил этап
    data = query.data
    context.user_data["region"] = int(data) if data != "SKIP" else None

    selected_label = REGION_MAP.get(data, "Не выбран")

    # Отправить пользователю клавиатуру для выбора формата работы
    await query.edit_message_text(
        f"📍 Регион: {selected_label}\n\n💻 Выберите формат работы:",
        reply_markup=build_keyboard(WORK_FORMAT_MAP)
    )
    return WORK_FORMAT


async def work_format_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем формат работы, переходим к занятости"""

    # Ожидать выбор пользователем формата работы
    query = update.callback_query
    await query.answer()

    # Извлечь из ответа формат работы, если этап не пропущен пользователем
    data = query.data
    context.user_data["work_format"] = data if data != "SKIP" else None

    selected_label = WORK_FORMAT_MAP.get(data, "Не выбран")

    # Отправить пользователю клавиатуру для выбора типа занятости
    await query.edit_message_text(
        f"💻 Формат работы: {selected_label}\n\n📝 Выберите тип занятости:",
        reply_markup=build_keyboard(EMPLOYMENT_MAP)
    )
    return EMPLOYMENT_FORM


async def employment_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем занятость, переходим к опыту"""

    # Ожидать выбор пользователем типа занятости
    query = update.callback_query
    await query.answer()

    # Извлечь из ответа тип занятости, если пользователь не пропустил этап
    data = query.data
    context.user_data["employment_form"] = data if data != "SKIP" else None

    selected_label = EMPLOYMENT_MAP.get(data, "Не выбрана")

    # Отправить пользователю клавиатуру для выбора опыта работы
    await query.edit_message_text(
        f"📝 Занятость: {selected_label}\n\n🎓 Выберите требуемый опыт:",
        reply_markup=build_keyboard(EXPERIENCE_MAP)
    )
    return EXPERIENCE


async def experience_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Финальный шаг: сохраняем опыт, формируем URL и выводим результат"""

    # Ожидать выбор пользователем опыта работы
    query = update.callback_query
    await query.answer()

    # Извлечь из ответа опыт работы, если пользователь не пропустил этап
    data = query.data
    context.user_data["experience"] = data if data != "SKIP" else None

    # Сформировать итоговый URL для получения вакансий из ленты с заданными фильтрами
    rss_url = create_rss_request_url(
        search_text=context.user_data.get("search_text", ""),
        region=context.user_data.get("region"),
        work_format=context.user_data.get("work_format"),
        employment_form=context.user_data.get("employment_form"),
        required_experience=context.user_data.get("experience")
    )

    # Сохранить подписку на вакансии в базе данных
    add_rss_subscription(
        user_id=query.from_user.id,
        rss_url=rss_url
    )

    # Собрать отчёт о выбранных параметрах
    summary_lines = [
        "✅ *Подписка оформлена!*",
        "",
        f"🔍 *Запрос:* {context.user_data['search_text']}",
        f"📍 *Регион:* {REGION_MAP.get(str(context.user_data.get('region', '')), 'Не выбран')}",
        f"💻 *Формат:* {WORK_FORMAT_MAP.get(context.user_data.get('work_format', ''), 'Не выбран')}",
        f"📝 *Занятость:* {EMPLOYMENT_MAP.get(context.user_data.get('employment_form', ''), 'Не выбрана')}",
        f"🎓 *Опыт:* {EXPERIENCE_MAP.get(context.user_data.get('experience', ''), 'Не выбран')}",
        "",
        f"🔗 [Открыть RSS-ленту]({rss_url})",
    ]

    await query.edit_message_text(
        text="\n".join(summary_lines),
        parse_mode="Markdown",
        disable_web_page_preview=False,
    )

    log.info(f"Subscribe completed: {rss_url}")
    return ConversationHandler.END


async def subscribe_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик отмены диалога"""
    await update.message.reply_text("❌ Оформление подписки отменено.")
    return ConversationHandler.END


# ==================== Запуск бота ====================

def run_bot():
    log.info("Starting Telegram bot...")

    # ConversationHandler для /subscribe
    subscribe_conv = ConversationHandler(
        entry_points=[CommandHandler("subscribe", subscribe_command_handler)],
        states={
            SEARCH_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_text_received),
            ],
            REGION: [
                CallbackQueryHandler(region_selected),
                MessageHandler(filters.TEXT & ~filters.COMMAND, unsubscribe_command_handler),
            ],
            WORK_FORMAT: [
                CallbackQueryHandler(work_format_selected),
                MessageHandler(filters.TEXT & ~filters.COMMAND, unsubscribe_command_handler),
            ],
            EMPLOYMENT_FORM: [
                CallbackQueryHandler(employment_selected),
                MessageHandler(filters.TEXT & ~filters.COMMAND, unsubscribe_command_handler),
            ],
            EXPERIENCE: [
                CallbackQueryHandler(experience_selected),
                MessageHandler(filters.TEXT & ~filters.COMMAND, unsubscribe_command_handler),
            ],
        },
        fallbacks=[CommandHandler("cancel", subscribe_cancel)],
    )

    app.add_handlers([
        CommandHandler("start", start_command_handler),
        CommandHandler("help", help_command_handler),
        CommandHandler("unsubscribe", unsubscribe_command_handler),
        CommandHandler("reset", reset_command_handler),
        CommandHandler("show_subscriptions", show_subscriptions_command_handler),
        subscribe_conv,
    ])

    log.info("Run polling...")
    app.run_polling()
    log.info("Telegram bot stopped...")

