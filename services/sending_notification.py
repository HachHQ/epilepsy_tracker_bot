@main_menu_router.message(F.text.startswith("admin."))
async def get_login_from_user(message: Message):
    text_fin = message.text.split(".")[1]
    print(text_fin)
    db = SessionLocal()
    try:
        existing_by_login = db.query(User).filter(User.login == text_fin).first()
        if not existing_by_login:
            await message.answer(text=f"Пользователь с логином '{text_fin}' не существует, попробуйте ввести другой.",
            parse_mode="HTML")
            return
        await message.answer(
            text=f"Вот данные пользователя {existing_by_login.login}: \n {existing_by_login.telegram_id} \n {existing_by_login.telegram_username} \n {existing_by_login.telegram_fullname} \n {existing_by_login.name} \n {existing_by_login.created_at} ",
            parse_mode="HTML"
        )
        print("Пользователь успешно найден")
        await get_notification_queue().send_notification(chat_id=existing_by_login.telegram_id, text=f"{existing_by_login.name}, вам перевели 1 000 000 ФПИ Банок")
        print("Пользователю успешно отправлено уведомление.")
    except InterruptedError as e:
        print(f"Ошибка создания пользователя: {e}")
        db.rollback()
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")
    finally:
        db.close()