"""
Telegram command handlers for custom tracking system.
Epic 006 - Phase 5: User-facing tracker management
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from uuid import UUID, uuid4
from datetime import datetime

from src.models.tracking import TrackerDefinition, TrackerEntry
from src.models.tracker_templates import TRACKER_TEMPLATES, get_template, list_template_names
from src.db.queries import (
    create_tracking_category,
    get_tracking_categories,
    save_tracking_entry,
    get_recent_tracker_entries
)
from src.utils.tracker_validation import TrackerValidator, validate_and_create_entry

logger = logging.getLogger(__name__)

# Conversation states
(
    CHOOSE_TEMPLATE,
    SELECT_TEMPLATE,
    CUSTOM_NAME,
    ADD_FIELDS,
    CONFIRM_TRACKER,
    SELECT_LOG_TRACKER,
    LOG_FIELD_VALUES,
    ADD_NOTES,
    SELECT_VIEW_TRACKER
) = range(9)


# ================================================================
# /create_tracker command - Create new custom tracker
# ================================================================

async def create_tracker_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start tracker creation flow"""
    keyboard = [
        [InlineKeyboardButton("📋 Use Template", callback_data="use_template")],
        [InlineKeyboardButton("✨ Create Custom (Coming Soon)", callback_data="create_custom_soon")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎯 **Create a New Tracker**\n\n"
        "Custom trackers let you monitor any health metric you want:\n"
        "• Period cycles & symptoms\n"
        "• Energy levels\n"
        "• Mood & emotions\n"
        "• Medications\n"
        "• Sleep quality\n"
        "• Exercise\n"
        "• And more!\n\n"
        "Choose an option:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    return CHOOSE_TEMPLATE


async def show_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available tracker templates"""
    query = update.callback_query
    await query.answer()

    keyboard = []
    for template_id, template_name, icon in list_template_names():
        keyboard.append([
            InlineKeyboardButton(
                f"{icon} {template_name}",
                callback_data=f"template_{template_id}"
            )
        ])
    keyboard.append([InlineKeyboardButton("« Back", callback_data="back_to_start")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "📋 **Choose a Template**\n\n"
        "Select a predefined tracker to get started quickly:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    return SELECT_TEMPLATE


async def create_from_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create tracker from selected template"""
    query = update.callback_query
    await query.answer()

    # Extract template ID from callback data
    template_id = query.data.replace("template_", "")
    template = get_template(template_id)

    if not template:
        await query.edit_message_text("❌ Template not found. Please try again.")
        return ConversationHandler.END

    try:
        telegram_id = str(update.effective_user.id)

        # Check if tracker with this name already exists
        existing = await get_tracking_categories(telegram_id, active_only=True)
        if any(cat["name"] == template["name"] for cat in existing):
            await query.edit_message_text(
                f"⚠️ You already have a tracker named '{template['name']}'.\n\n"
                f"Please delete the old one first or use /view_tracker to see it."
            )
            return ConversationHandler.END

        # Create tracker from template
        # Note: This uses the old TrackingCategory model for compatibility
        # TODO: Migrate to TrackerDefinition in future
        from src.models.tracking import TrackingCategory, TrackingField, TrackingSchedule

        # Convert template fields to TrackingField objects
        fields = {}
        for field_name, field_config in template["fields"].items():
            fields[field_name] = TrackingField(
                type=field_config["type"],
                label=field_config["label"],
                min_value=field_config.get("min_value"),
                max_value=field_config.get("max_value"),
                required=field_config.get("required", True)
            )

        # Create schedule if exists
        schedule = None
        if "schedule" in template:
            sched = template["schedule"]
            schedule = TrackingSchedule(
                type=sched["type"],
                time=sched["time"],
                days=sched.get("days", list(range(7))),
                message=sched["message"]
            )

        tracker = TrackingCategory(
            id=uuid4(),
            user_id=telegram_id,
            name=template["name"],
            fields=fields,
            schedule=schedule,
            active=True
        )

        await create_tracking_category(tracker)

        # Build success message with field info
        field_list = "\n".join([
            f"   • {field['label']} ({field['type']})"
            for field in template["fields"].values()
        ])

        success_msg = (
            f"✅ **Tracker Created!**\n\n"
            f"{template['icon']} **{template['name']}**\n\n"
            f"**Fields:**\n{field_list}\n\n"
            f"Use /log_tracker to start logging data!"
        )

        await query.edit_message_text(success_msg, parse_mode="Markdown")

        logger.info(f"Created tracker '{template['name']}' for user {telegram_id}")

    except Exception as e:
        logger.error(f"Failed to create tracker from template: {e}")
        await query.edit_message_text(
            f"❌ Failed to create tracker: {str(e)}\n\n"
            f"Please try again later."
        )

    return ConversationHandler.END


async def create_custom_soon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder for custom tracker creation"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "✨ **Custom Tracker Creation**\n\n"
        "Fully custom trackers are coming soon!\n\n"
        "For now, please use one of our templates. "
        "They cover most common health tracking needs. 😊"
    )

    return ConversationHandler.END


async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel tracker creation"""
    await update.message.reply_text("❌ Tracker creation cancelled.")
    return ConversationHandler.END


# ================================================================
# /log_tracker command - Log tracker entry
# ================================================================

async def log_tracker_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start tracker entry logging flow"""
    telegram_id = str(update.effective_user.id)

    try:
        # Get user's trackers
        categories = await get_tracking_categories(telegram_id, active_only=True)

        if not categories:
            await update.message.reply_text(
                "📊 You don't have any trackers yet!\n\n"
                "Use /create_tracker to create one."
            )
            return ConversationHandler.END

        # Show tracker selection
        keyboard = []
        for cat in categories:
            icon = cat.get("icon", "📊")
            keyboard.append([
                InlineKeyboardButton(
                    f"{icon} {cat['name']}",
                    callback_data=f"log_{cat['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_log")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📝 **Log Tracker Entry**\n\n"
            "Which tracker do you want to log to?",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        return SELECT_LOG_TRACKER

    except Exception as e:
        logger.error(f"Failed to start log tracker: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return ConversationHandler.END


async def log_tracker_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tracker selection for logging"""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_log":
        await query.edit_message_text("❌ Logging cancelled.")
        return ConversationHandler.END

    # Extract tracker ID
    tracker_id = query.data.replace("log_", "")
    context.user_data["logging_tracker_id"] = tracker_id

    telegram_id = str(update.effective_user.id)

    try:
        # Get tracker details
        categories = await get_tracking_categories(telegram_id)
        tracker = next((c for c in categories if str(c["id"]) == tracker_id), None)

        if not tracker:
            await query.edit_message_text("❌ Tracker not found.")
            return ConversationHandler.END

        context.user_data["logging_tracker"] = tracker
        context.user_data["logging_data"] = {}

        # Start collecting field values
        # For simplicity, we'll ask for all fields in one message
        fields_text = "Please enter values for the following fields:\n\n"
        for field_name, field_config in tracker["fields"].items():
            field_type = field_config.get("type", "text")
            label = field_config.get("label", field_name)
            required = field_config.get("required", True)
            req_marker = "* (required)" if required else "(optional)"

            fields_text += f"**{label}** {req_marker}\n"
            fields_text += f"   Type: {field_type}\n"

            if field_type == "rating":
                min_val = field_config.get("min_value", 1)
                max_val = field_config.get("max_value", 10)
                fields_text += f"   Range: {min_val}-{max_val}\n"
            elif field_type in ["multiselect", "single_select"]:
                options = field_config.get("options", [])
                fields_text += f"   Options: {', '.join(options)}\n"

            fields_text += "\n"

        fields_text += (
            "\n**Format**: One value per line\n"
            "Example:\n"
            "level: 7\n"
            "quality: felt energized\n\n"
            "Send your values now:"
        )

        await query.edit_message_text(fields_text, parse_mode="Markdown")

        return LOG_FIELD_VALUES

    except Exception as e:
        logger.error(f"Failed to select tracker for logging: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)}")
        return ConversationHandler.END


async def log_field_values(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parse and save field values"""
    telegram_id = str(update.effective_user.id)
    tracker = context.user_data.get("logging_tracker")

    if not tracker:
        await update.message.reply_text("❌ Session expired. Please start over with /log_tracker")
        return ConversationHandler.END

    try:
        # Parse user input (simple key:value format)
        data = {}
        lines = update.message.text.strip().split("\n")

        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                # Try to convert to appropriate type
                field_config = tracker["fields"].get(key)
                if not field_config:
                    continue

                field_type = field_config.get("type", "text")

                if field_type in ["number", "rating"]:
                    try:
                        data[key] = float(value) if "." in value else int(value)
                    except ValueError:
                        await update.message.reply_text(
                            f"❌ '{value}' is not a valid number for field '{key}'.\n"
                            f"Please try again with /log_tracker"
                        )
                        return ConversationHandler.END
                elif field_type == "boolean":
                    data[key] = value.lower() in ["true", "yes", "1", "y"]
                elif field_type == "multiselect":
                    data[key] = [v.strip() for v in value.split(",")]
                else:
                    data[key] = value

        if not data:
            await update.message.reply_text(
                "❌ No valid data found. Please use format:\n"
                "field_name: value\n\n"
                "Try again with /log_tracker"
            )
            return ConversationHandler.END

        # Validate data
        # TODO: Use TrackerValidator for proper validation
        # For now, just save it
        entry = TrackerEntry(
            id=uuid4(),
            user_id=telegram_id,
            category_id=UUID(tracker["id"]),
            timestamp=datetime.now(),
            data=data,
            notes=None
        )

        await save_tracking_entry(entry)

        success_msg = (
            f"✅ **Entry Logged!**\n\n"
            f"{tracker.get('icon', '📊')} **{tracker['name']}**\n\n"
            f"**Logged values:**\n"
        )
        for key, value in data.items():
            success_msg += f"• {key}: {value}\n"

        await update.message.reply_text(success_msg, parse_mode="Markdown")

        logger.info(f"Logged tracker entry for {tracker['name']} by user {telegram_id}")

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Failed to log tracker entry: {e}")
        await update.message.reply_text(f"❌ Failed to save entry: {str(e)}")
        return ConversationHandler.END


# ================================================================
# /view_tracker command - View tracker data
# ================================================================

async def view_tracker_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start viewing tracker data"""
    telegram_id = str(update.effective_user.id)

    try:
        categories = await get_tracking_categories(telegram_id, active_only=True)

        if not categories:
            await update.message.reply_text(
                "📊 You don't have any trackers yet!\n\n"
                "Use /create_tracker to create one."
            )
            return ConversationHandler.END

        # Show tracker selection
        keyboard = []
        for cat in categories:
            icon = cat.get("icon", "📊")
            keyboard.append([
                InlineKeyboardButton(
                    f"{icon} {cat['name']}",
                    callback_data=f"view_{cat['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_view")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📊 **View Tracker Data**\n\n"
            "Which tracker do you want to view?",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        return SELECT_VIEW_TRACKER

    except Exception as e:
        logger.error(f"Failed to start view tracker: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return ConversationHandler.END


async def view_tracker_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show tracker data"""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_view":
        await query.edit_message_text("❌ Viewing cancelled.")
        return ConversationHandler.END

    tracker_id = query.data.replace("view_", "")
    telegram_id = str(update.effective_user.id)

    try:
        # Get tracker
        categories = await get_tracking_categories(telegram_id)
        tracker = next((c for c in categories if str(c["id"]) == tracker_id), None)

        if not tracker:
            await query.edit_message_text("❌ Tracker not found.")
            return ConversationHandler.END

        # Get recent entries
        entries = await get_recent_tracker_entries(
            user_id=telegram_id,
            category_id=UUID(tracker_id),
            limit=10
        )

        icon = tracker.get("icon", "📊")
        message = f"{icon} **{tracker['name']}**\n\n"

        if not entries:
            message += "No entries yet. Use /log_tracker to add your first entry!"
        else:
            message += f"**Recent entries** (showing {len(entries)}):\n\n"
            for entry in entries:
                timestamp = entry["timestamp"]
                data = entry["data"]

                message += f"📅 {timestamp.strftime('%Y-%m-%d %H:%M')}\n"
                for field, value in data.items():
                    message += f"   • {field}: {value}\n"
                if entry.get("notes"):
                    message += f"   💭 {entry['notes']}\n"
                message += "\n"

        message += "\n💡 Tip: Ask me questions about your tracker data!\n"
        message += "   Example: \"Show me my energy levels this week\""

        await query.edit_message_text(message, parse_mode="Markdown")

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Failed to view tracker: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)}")
        return ConversationHandler.END


# ================================================================
# /my_trackers command - List all trackers
# ================================================================

async def my_trackers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all user's trackers"""
    telegram_id = str(update.effective_user.id)

    try:
        categories = await get_tracking_categories(telegram_id, active_only=True)

        if not categories:
            await update.message.reply_text(
                "📊 **Your Trackers**\n\n"
                "You don't have any trackers yet!\n\n"
                "Use /create_tracker to create your first tracker.",
                parse_mode="Markdown"
            )
            return

        message = "📊 **Your Active Trackers**\n\n"
        for cat in categories:
            icon = cat.get("icon", "📊")
            name = cat["name"]
            field_count = len(cat["fields"])
            fields = ", ".join(cat["fields"].keys())

            message += f"{icon} **{name}**\n"
            message += f"   Fields ({field_count}): {fields}\n\n"

        message += "\n**Commands:**\n"
        message += "• /log_tracker - Log new entry\n"
        message += "• /view_tracker - View recent data\n"
        message += "• /create_tracker - Create new tracker\n"

        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Failed to list trackers: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# ================================================================
# Conversation handler setup
# ================================================================

tracker_creation_handler = ConversationHandler(
    entry_points=[CommandHandler("create_tracker", create_tracker_start)],
    states={
        CHOOSE_TEMPLATE: [
            CallbackQueryHandler(show_templates, pattern="^use_template$"),
            CallbackQueryHandler(create_custom_soon, pattern="^create_custom_soon$"),
        ],
        SELECT_TEMPLATE: [
            CallbackQueryHandler(create_from_template, pattern="^template_"),
            CallbackQueryHandler(create_tracker_start, pattern="^back_to_start$"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_creation)],
    name="tracker_creation",
    persistent=False
)

tracker_logging_handler = ConversationHandler(
    entry_points=[CommandHandler("log_tracker", log_tracker_start)],
    states={
        SELECT_LOG_TRACKER: [
            CallbackQueryHandler(log_tracker_selected, pattern="^log_"),
            CallbackQueryHandler(log_tracker_selected, pattern="^cancel_log$"),
        ],
        LOG_FIELD_VALUES: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, log_field_values)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_creation)],
    name="tracker_logging",
    persistent=False
)

tracker_viewing_handler = ConversationHandler(
    entry_points=[CommandHandler("view_tracker", view_tracker_start)],
    states={
        SELECT_VIEW_TRACKER: [
            CallbackQueryHandler(view_tracker_selected, pattern="^view_"),
            CallbackQueryHandler(view_tracker_selected, pattern="^cancel_view$"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_creation)],
    name="tracker_viewing",
    persistent=False
)
