#!/usr/bin/env python3
"""
KesslerHealthBot - Oura Telegram Bot with Polling

Usage:
    python telegram_bot.py
    # Runs in background: nohup python telegram_bot.py &

Features:
    /start - Welcome message
    /sleep - Today's sleep
    /readiness - Today's readiness
    /report - Weekly report
    /alerts - Recent alerts
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
except ImportError:
    print("Install python-telegram-bot: pip install python-telegram-bot")
    sys.exit(1)

import requests

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token from environment
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN not set")
    sys.exit(1)

OURA_API_TOKEN = os.environ.get("OURA_API_TOKEN")
if not OURA_API_TOKEN:
    print("Error: OURA_API_TOKEN not set. Get it from https://cloud.ouraring.com/personal-access-tokens")
    sys.exit(1)


class OuraClient:
    BASE_URL = "https://api.ouraring.com/v2/usercollection"
    
    def __init__(self, token):
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}
    
    def get_recent_sleep(self, days=2):
        # Oura data is processed with delay - get last few days
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

        # Get daily sleep scores
        resp_daily = requests.get(
            f"{self.BASE_URL}/daily_sleep",
            headers=self.headers,
            params={"start_date": start, "end_date": end}
        )
        daily_data = {item["day"]: item for item in resp_daily.json().get("data", [])}

        # Get detailed sleep data
        resp_sleep = requests.get(
            f"{self.BASE_URL}/sleep",
            headers=self.headers,
            params={"start_date": start, "end_date": end}
        )
        sleep_data = resp_sleep.json().get("data", [])

        # Merge: add scores to sleep data
        for item in sleep_data:
            day = item.get("day")
            if day in daily_data:
                item["score"] = daily_data[day].get("score")

        # Return last N entries
        return sleep_data[-days:] if len(sleep_data) >= days else sleep_data
    
    def get_weekly_summary(self):
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        resp = requests.get(
            f"{self.BASE_URL}/sleep",
            headers=self.headers,
            params={"start_date": start, "end_date": end}
        )
        return resp.json().get("data", [])


oura = OuraClient(OURA_API_TOKEN)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "🤖 *KesslerHealthBot*\n\n"
        "Your Oura Health Assistant\n\n"
        "Commands:\n"
        "• /sleep - Today's sleep data\n"
        "• /readiness - Today's readiness\n"
        "• /report - Weekly summary\n"
        "• /alerts - Recent alerts\n"
        "• /help - This message",
        parse_mode="Markdown"
    )


async def sleep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sleep command"""
    data = oura.get_recent_sleep(days=2)

    if not data:
        await update.message.reply_text("❌ No recent sleep data found. Make sure your Oura ring is synced.")
        return

    msg = "😴 *Recent Sleep*\n\n"

    for i, day_data in enumerate(reversed(data)):
        day = day_data.get("day")
        hours = round(day_data.get("total_sleep_duration", 0) / 3600, 1)
        efficiency = day_data.get("efficiency", "N/A")
        hrv = day_data.get("average_hrv", "N/A")
        score = day_data.get("score", "N/A")

        label = "📅 Latest" if i == 0 else "📅 Previous"
        msg += f"{label} *({day})*\n"
        msg += f"  Sleep Score: *{score}*/100\n"
        msg += f"  Duration: *{hours}h*\n"
        msg += f"  Efficiency: *{efficiency}%*\n"
        msg += f"  HRV: *{hrv} ms*\n"

        if i < len(data) - 1:
            msg += "\n"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def readiness(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /readiness command"""
    data_list = oura.get_recent_sleep(days=2)

    if not data_list:
        await update.message.reply_text("❌ No recent data found. Make sure your Oura ring is synced.")
        return

    data = data_list[-1]  # Get most recent for readiness
    
    readiness = data.get("readiness", {})
    score = readiness.get("score", "N/A")
    
    msg = f"⚡ *Today's Readiness*\n\n"
    msg += f"Score: *{score}*/100\n\n"
    
    # Contributors
    contrib = readiness.get("contributors", {})
    if contrib:
        msg += "_Contributors:_\n"
        for key, value in contrib.items():
            msg += f"• {key.replace('_', ' ').title()}: {value}\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /report command"""
    data = oura.get_weekly_summary()
    
    if not data:
        await update.message.reply_text("❌ No data for this week.")
        return
    
    # Calculate averages
    scores = []
    efficiencies = []
    hours = []
    readies = []
    
    for day in data:
        scores.append(day.get("score", 0))
        efficiencies.append(day.get("efficiency", 0))
        hours.append(day.get("total_sleep_duration", 0) / 3600)
        r = day.get("readiness", {}).get("score")
        if r:
            readies.append(r)
    
    avg_score = round(sum(scores) / len(scores), 1)
    avg_eff = round(sum(efficiencies) / len(efficiencies), 1)
    avg_hours = round(sum(hours) / len(hours), 1)
    avg_readiness = round(sum(readies) / len(readies), 1) if readies else "N/A"
    
    msg = f"📊 *Weekly Report*\n\n"
    msg += f"Avg Sleep Score: *{avg_score}*/100\n"
    msg += f"Avg Readiness: *{avg_readiness}*/100\n"
    msg += f"Avg Sleep: *{avg_hours}h*\n"
    msg += f"Avg Efficiency: *{avg_eff}%*\n"
    msg += f"\n_Tracked: {len(data)} days_"
    
    await update.message.reply_text(msg, parse_mode="Markdown")


async def alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /alerts command"""
    data = oura.get_weekly_summary()
    
    if not data:
        await update.message.reply_text("❌ No data available.")
        return
    
    alert_days = []
    for day in data:
        readiness = day.get("readiness", {}).get("score", 100)
        efficiency = day.get("efficiency", 100)
        hours = day.get("total_sleep_duration", 0) / 3600
        
        alerts = []
        if readiness < 70:
            alerts.append(f"Readiness {readiness}")
        if efficiency < 80:
            alerts.append(f"Efficiency {efficiency}%")
        if hours < 6:
            alerts.append(f"Sleep {hours:.1f}h")
        
        if alerts:
            alert_days.append({"day": day.get("day"), "alerts": alerts})
    
    if not alert_days:
        await update.message.reply_text("✅ No alerts! Everything looks good.")
        return
    
    msg = "⚠️ *Recent Alerts*\n\n"
    for alert in alert_days[-5:]:
        msg += f"📅 *{alert['day']}*\n"
        for a in alert['alerts']:
            msg += f"   • {a}\n"
        msg += "\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await start(update, context)


def main():
    """Run the bot"""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sleep", sleep))
    app.add_handler(CommandHandler("readiness", readiness))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("alerts", alerts))
    app.add_handler(CommandHandler("help", help_command))
    
    print("🤖 KesslerHealthBot started!")
    print("Send /start to your bot on Telegram")
    
    # Start polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
