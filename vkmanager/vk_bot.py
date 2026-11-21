import os
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

# Берем данные из переменных окружения Railway (безопасно!)
VK_TOKEN = os.getenv("VK_TOKEN")
VK_GROUP_ID = int(os.getenv("VK_GROUP_ID"))

def main():
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    longpoll = VkLongPoll(vk_session)
    vk = vk_session.get_api()

    print("✅ VK Бот SYNTH запущен и слушает сообщения...")

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id = event.user_id
            text = event.text.lower().strip()

            print(f"📩 Новое сообщение от {user_id}: '{event.text}'")

            if text in ["привет", "здравствуйте", "хай"]:
                response = "Привет! 👋 Я виртуальный помощник SYNTH. Опишите вашу задачу, и я передам её менеджеру."
            elif text in ["цена", "сколько стоит", "бюджет"]:
                response = "Стоимость разработки зависит от сложности задачи. Минимальный бюджет — от 500 ⭐ (Telegram Stars). Опишите, что нужно сделать, и мы оценим проект!"
            elif text in ["контакты", "телеграм", "tg", "тг"]:
                response = "📱 Наш основной рабочий чат и бот для заказов находится в Telegram: @Synthmanager_bot\n\nТам мы отвечаем быстрее всего!"
            else:
                response = (
                    "Спасибо за ваше сообщение! 📩\n\n"
                    "Менеджер SYNTH скоро изучит его и ответит вам.\n"
                    "Для более быстрой связи рекомендуем написать нам в Telegram: @Synthmanager_bot"
                )

            try:
                vk.messages.send(
                    user_id=user_id,
                    message=response,
                    random_id=0 # Обязательный параметр для API VK
                )
                print(f"✅ Ответ отправлен пользователю {user_id}")
            except Exception as e:
                print(f"❌ Ошибка отправки: {e}")

if __name__ == '__main__':
    main()
