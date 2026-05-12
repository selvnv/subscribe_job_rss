import asyncio
import html
import os
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    filters, ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler
)

from modules.log.log import log
from modules.constants import (
    WORK_FORMAT_MAP, EMPLOYMENT_MAP, EXPERIENCE_MAP, REGION_MAP
)
from modules.parser import create_rss_request_url, parse_rss_url_to_dict, parse_rss_feed, parse_vacancy
from modules.templates import render_rss_params_template, render_job_card_template
from modules.db import add_rss_subscription, list_user_rss_subscriptions, dict_rss_subscriptions, \
    is_vacancy_already_sent, mark_vacancy_as_sent, delete_rss_subscription


load_dotenv()
TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
if not TELEGRAM_API_TOKEN:
    raise RuntimeError("TELEGRAM_API_TOKEN is not set in .env file")

try:
    RSS_CHECK_INTERVAL = int(os.getenv("RSS_CHECK_INTERVAL_SECONDS", "3600"))
except ValueError:
    log.warning(
        "Invalid RSS_CHECK_INTERVAL_SECONDS value, using default 3600 seconds"
    )
    RSS_CHECK_INTERVAL = 3600

VACANCIES_PARSE_LIMIT = 3


# Состояния диалога
(SEARCH_TEXT, REGION, WORK_FORMAT, EMPLOYMENT_FORM, EXPERIENCE, UNSELECT) = range(6)


app = ApplicationBuilder().token(TELEGRAM_API_TOKEN).build()


def build_keyboard(options_map: dict, skip_callback: str = "SKIP") -> InlineKeyboardMarkup:
    """Строит клавиатуру из словаря {callback_data: label} + кнопка Пропустить"""
    buttons = [
        [InlineKeyboardButton(label, callback_data=data)]
        for data, label in options_map.items()
    ]
    buttons.append([InlineKeyboardButton("⏭ Пропустить", callback_data=skip_callback)])
    return InlineKeyboardMarkup(buttons)


async def unexpected_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        "/show_subscriptions - Показать активные подписки",
        "/subscribe – Подписаться на рассылку вакансий с заданными параметрами",
        "/unsubscribe – Отказаться от рассылки по определённым параметрам",
        "/reset – Отказаться от всех действующих рассылок"
    ])
    await update.message.reply_text(text=help_text)


async def show_subscriptions_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    subscriptions = list_user_rss_subscriptions(user_id)

    if not subscriptions:
        await update.message.reply_text("📝 У вас нет активных подписок.")
        return

    message = ""
    for _, _, rss_url in subscriptions:
        params = parse_rss_url_to_dict(rss_url)
        message += render_rss_params_template("templates/rss_params_message.html", params)
        message += "\n"

    await update.message.reply_text(
        f"📝 <b>Ваши подписки:</b>\n{message}" if message else "❌ Ошибка при получении активных подписок",
        parse_mode='HTML'
    )


async def send_vacancies_info(context: ContextTypes.DEFAULT_TYPE = None):
    """Периодическая задача: парсит RSS-ленты и рассылает новые вакансии подписчикам.
       Дедуплицирует RSS-запросы: если у нескольких пользователей одинаковый URL,
       лента парсится один раз, а результаты рассылаются всем подписчикам."""
    users_rss = dict_rss_subscriptions()

    # Группируем подписки по URL: один RSS-запрос для одинаковых URL
    url_to_users: dict[str, list[str]] = {}
    for user_id, subscriptions in users_rss.items():
        for subscription in subscriptions:
            rss_url = subscription.get("url")
            if rss_url:
                if rss_url not in url_to_users:
                    url_to_users[rss_url] = []
                url_to_users[rss_url].append(user_id)

    for rss_url, user_ids in url_to_users.items():
        try:
            log.info(f"Load RSS {rss_url} for {len(user_ids)} user(s)...")
            rss_items = parse_rss_feed(rss_url)
            log.info(f"Find {len(rss_items)} items...")

            if not rss_items:
                continue

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

            # Рассылаем каждую вакансию всем подписчикам этого URL
            for vac in results:
                for user_id in user_ids:
                    try:
                        # Не отправлять вакансию пользователю повторно
                        if is_vacancy_already_sent(user_id, vac['url']):
                            continue

                        vac['rss_url'] = rss_url

                        job_card = render_job_card_template(
                            template_path="./templates/jobs.html",
                            vacancy=vac
                        )

                        await app.bot.send_message(
                            chat_id=user_id,
                            text=job_card,
                            parse_mode="HTML"
                        )

                        mark_vacancy_as_sent(user_id, vac['url'])
                    except Exception as e:
                        log.error(f"Failed to send vacancy to user {user_id}: {e}")

        except Exception as e:
            log.error(f"Failed to process subscription {rss_url}: {e}")


# ==================== ConversationHandler: /unsubscribe ====================

async def unsubscribe_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 1: показываем список подписок и запрашиваем номер для удаления"""
    user_id = str(update.effective_user.id)
    subscriptions = list_user_rss_subscriptions(user_id)

    if not subscriptions:
        await update.message.reply_text("📝 У вас нет активных подписок.")
        return ConversationHandler.END

    # Формируем читаемый список
    lines = ["📝 <b>Ваши подписки:</b>\n"]
    for idx, (sub_id, _, rss_url) in enumerate(subscriptions, 1):
        params = parse_rss_url_to_dict(rss_url)
        # Рендерим компактное описание
        card = render_rss_params_template("templates/rss_params_message.html", params)
        lines.append(f"<b>#{idx}</b> {card}")

    # Сохраняем список во временные данные для следующего шага
    context.user_data["unsub_list"] = subscriptions

    lines.append("\n✏️ <b>Введите номер подписки, которую хотите удалить</b> (или /cancel для отмены):")

    await update.message.reply_text(
        text="\n".join(lines),
        parse_mode="HTML"
    )
    return UNSELECT


async def unsubscribe_number_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 2: удаляем выбранную подписку"""
    raw = update.message.text.strip()
    subscriptions = context.user_data.get("unsub_list", [])

    # Валидация: должно быть число в пределах списка
    try:
        choice = int(raw)
    except ValueError:
        await update.message.reply_text("⚠️ Введите число — номер подписки из списка.")
        return UNSELECT

    if choice < 1 or choice > len(subscriptions):
        await update.message.reply_text(
            f"⚠️ Номер должен быть от 1 до {len(subscriptions)}. Попробуйте снова."
        )
        return UNSELECT

    sub_id, _, rss_url = subscriptions[choice - 1]
    deleted_url = delete_rss_subscription(sub_id)

    if deleted_url:
        await update.message.reply_text(
            f"✅ Подписка удалена:\n<code>{html.escape(deleted_url)}</code>",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("❌ Не удалось удалить подписку.")

    log.info(f"User {str(update.effective_user.id)} unsubscribed from {deleted_url}")
    return ConversationHandler.END


async def unsubscribe_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Удаление подписки отменено.")
    return ConversationHandler.END


# ==================== /reset ====================

async def reset_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    subscriptions = list_user_rss_subscriptions(user_id)

    if not subscriptions:
        await update.message.reply_text("📝 У вас нет активных подписок.")
        return

    for sub_id, _, _ in subscriptions:
        delete_rss_subscription(sub_id)

    await update.message.reply_text(
        f"✅ Удалены все подписки ({len(subscriptions)} шт.)."
    )


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
    if not update.message.text.strip():
        await update.message.reply_text(
            "⚠️ Поисковый запрос не может быть пустым. Пожалуйста, введите текст:"
        )
        return SEARCH_TEXT

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
    context.user_data["region"] = data if data != "SKIP" else None

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

    try:
        # Сформировать итоговый URL для получения вакансий из ленты с заданными фильтрами
        rss_url = create_rss_request_url(
            search_text=context.user_data.get("search_text", ""),
            region=context.user_data.get("region"),
            work_format=context.user_data.get("work_format"),
            employment_form=context.user_data.get("employment_form"),
            required_experience=context.user_data.get("experience")
        )
    except Exception as e:
        log.error(f"Error while creating rss request url: {e}")
        await query.edit_message_text(
            text="❌ Не удалось сохранить подписку. Попробуйте позже.",
            parse_mode="HTML"
        )
        return ConversationHandler.END

    # Сохранить подписку на вакансии в базе данных
    is_rss_added = add_rss_subscription(
        user_id=query.from_user.id,
        rss_url=rss_url
    )

    # Собрать отчёт о выбранных параметрах
    summary_lines = ["❌ <b>Ошибка при оформлении подписки.</b>"] if not is_rss_added else [
        "✅ <b>Подписка оформлена!</b>",
        "",
        f"🔍 <b>Запрос:</b> {html.escape(context.user_data['search_text'])}",
        f"📍 <b>Регион:</b> {
            html.escape(
                REGION_MAP.get(
                    context.user_data.get('region', ''), 
                    'Не выбран'
                )
            )
        }",
        f"💻 <b>Формат:</b> {
            html.escape(
                WORK_FORMAT_MAP.get(
                    context.user_data.get('work_format', ''), 
                    'Не выбран'
                )
            )
        }",
        f"📝 <b>Занятость:</b> {
            html.escape(
                EMPLOYMENT_MAP.get(
                    context.user_data.get('employment_form', ''), 
                    'Не выбрана'
                )
            )
        }",
        f"🎓 <b>Опыт:</b> {
            html.escape(
                EXPERIENCE_MAP.get(
                    context.user_data.get('experience', ''), 
                    'Не выбран'
                )
            )
        }",
        "",
        f"🔗 [Открыть RSS-ленту]({rss_url})",
    ]

    await query.edit_message_text(
        text="\n".join(summary_lines),
        parse_mode="HTML"
    )

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
                MessageHandler(filters.TEXT & ~filters.COMMAND, unexpected_text_handler),
            ],
            WORK_FORMAT: [
                CallbackQueryHandler(work_format_selected),
                MessageHandler(filters.TEXT & ~filters.COMMAND, unexpected_text_handler),
            ],
            EMPLOYMENT_FORM: [
                CallbackQueryHandler(employment_selected),
                MessageHandler(filters.TEXT & ~filters.COMMAND, unexpected_text_handler),
            ],
            EXPERIENCE: [
                CallbackQueryHandler(experience_selected),
                MessageHandler(filters.TEXT & ~filters.COMMAND, unexpected_text_handler),
            ],
        },
        fallbacks=[CommandHandler("cancel", subscribe_cancel)],
    )

    # ConversationHandler для /unsubscribe
    unsubscribe_conv = ConversationHandler(
        entry_points=[CommandHandler("unsubscribe", unsubscribe_command_handler)],
        states={
            UNSELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, unsubscribe_number_received),
            ],
        },
        fallbacks=[CommandHandler("cancel", unsubscribe_cancel)],
    )

    app.add_handlers([
        CommandHandler("start", start_command_handler),
        CommandHandler("help", help_command_handler),
        CommandHandler("reset", reset_command_handler),
        CommandHandler("show_subscriptions", show_subscriptions_command_handler),
        subscribe_conv,
        unsubscribe_conv,
    ])

    # Запускаем периодическую задачу по проверке RSS-лент
    app.job_queue.run_repeating(
        send_vacancies_info,
        interval=RSS_CHECK_INTERVAL,
        first=10  # первый запуск через 10 секунд после старта
    )
    log.info(f"RSS check scheduled every {RSS_CHECK_INTERVAL} seconds.")

    log.info("Run polling...")
    app.run_polling()
    log.info("Telegram bot stopped...")

