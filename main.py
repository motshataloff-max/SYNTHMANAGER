async def three_day_report_task(bot: Bot):
    """Расширенный отчёт файлом раз в 3 дня (72 часа) в канал."""
    while True:
        await asyncio.sleep(259200)  # 72 часа
        try:
            stats = await db.general_stats()
            pr_list = await db.list_active_by_role("pr")  # Получаем список пиарщиков
            
            lines = [
                "=" * 50,
                f"📊 ПОДРОБНЫЙ ОТЧЁТ SYNTH (3 ДНЯ)",
                f"📅 {datetime.utcnow().strftime('%d.%m.%Y %H:%M')} UTC",
                "=" * 50,
                "",
                "📈 ОБЩАЯ СВОДКА:",
                f"👥 Всего пользователей: {stats['clients']}",
                f"📦 Активных проектов: {stats['active_projects']}",
                f"✅ Завершённых: {stats['done_projects']}",
                f"💰 Общий оборот: {stats['turnover']} ⭐",
                f"🏦 Счёт компании: {stats['company']} ⭐",
                "",
                "📣 СТАТИСТИКА ПИАРЩИКОВ:",
            ]
            
            for pr in pr_list:
                try:
                    s = await db.pr_stats(pr["telegram_id"])
                    lines.append(f"  👤 {pr['telegram_id']}: клиентов={s['clients']}, заказов={s['orders']}, оборот={s['total']}⭐")
                except Exception:
                    pass
            
            file_content = "\n".join(lines)
            file_bytes = file_content.encode("utf-8")
            
            await bot.send_document(
                chat_id=config.ping_chat_id,
                document=BufferedInputFile(file_bytes, filename=f"synth_3days_{datetime.utcnow().strftime('%Y%m%d')}.txt"),
                caption="📦 Автоматический отчёт SYNTH за последние 3 дня"
            )
        except Exception as e:
            logging.error(f"Ошибка отчёта за 3 дня: {e}")
