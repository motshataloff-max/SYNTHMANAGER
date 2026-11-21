import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

# ==========================================
# НАСТРОЙКИ (Вставь свои данные)
# ==========================================
TOKEN = "vk1.a.EtSut8PHNgB_jdfx5mrbAn4S4sSt1iE3vGmSqLMFuBjS0wJnrvl-GRzPfGvJ3H1JKaJWaYP8MXNU-yl75NKKts4LXpYqZGItcS142l2-Oh5Nos2hJ_U4OaNisLQ-4hjYw24P3wzJxz-1L_EeHpj-J2kflSmQh-kMeYPtdRyK7N4hfL96vHdDDYILFr__dj2hnysCYo5Gc1w5bJaYshlG5Q"
GROUP_ID = -241246302  # Твой ID сообщества (с минусом!)

def main():
    # 1. Подключаемся к API ВКонтакте
    vk_session = vk_api.VkApi(token=TOKEN)
    longpoll = VkLongPoll(vk_session)
    vk = vk_session.get_api()

    print("✅ VK Бот SYNTH запущен и слушает сообщения...")

    # 2. Бесконечный цикл прослушивания новых сообщений
    for event in longpoll.listen():
        # Реагируем только на новые входящие сообщения
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id = event.user_id
            text = event.text.lower().strip()

            print(f"📩 Новое сообщение от пользователя {user_id}: '{event.text}'")

            # 3. Простая логика ответов
            if text in ["привет", "здравствуйте", "хай"]:
                response = "Привет! 👋 Я виртуальный помощник SYNTH. Опишите вашу задачу, и я передам её менеджеру."
            
            elif text in ["цена", "сколько стоит", "бюджет"]:
                response = "Стоимость разработки зависит от сложности задачи. Минимальный бюджет — от 500 ⭐ (Telegram Stars). Опишите, что нужно сделать, и мы оценим проект!"
            
            elif text in ["контакты", "телеграм", "tg"]:
                response = "📱 Наш основной рабочий чат и бот для заказов находится в Telegram: @Synthmanager_bot\n\nТам мы отвечаем быстрее всего!"
            
            else:
                # Если сообщение не подходит под ключевые слова, даем универсальный ответ
                response = (
                    "Спасибо за ваше сообщение! 📩\n\n"
                    "Менеджер SYNTH скоро изучит его и ответит вам.\n"
                    "Для более быстрой связи рекомендуем написать нам в Telegram-бот: @Synthmanager_bot"
                )

            # 4. Отправляем ответ пользователю
            try:
                vk.messages.send(
                    user_id=user_id,
                    message=response,
                    random_id=0  # Обязательный параметр для новых версий API VK
                )
                print(f"✅ Ответ отправлен пользователю {user_id}")
            except Exception as e:
                print(f"❌ Ошибка отправки сообщения: {e}")

if __name__ == '__main__':
    main()
