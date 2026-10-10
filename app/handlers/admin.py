from datetime import datetime, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from app import config
from app.database import db
from app.locales import get_text

router = Router()
pending_grant = set()

async def admin_language(user_id):
    language = await db.get_user_language(user_id)
    return language if language in ("uz", "ru", "en", "ar", "ko", "zh") else "uz"


ADMIN_TEXTS = {
    "uz": {
        "title": "🛠 <b>RoastAI admin paneli</b>\\nBo‘limni tanlang:",
        "denied": "⛔ Bu bo‘lim faqat bot administratori uchun.",
        "permission": "Ruxsat yo‘q.",
        "grant_prompt": "👤 Foydalanuvchining Telegram ID raqamini yoki @username nomini yuboring.",
        "back": "⬅️ Admin panel",
    },
    "ru": {
        "title": "🛠 <b>Панель администратора RoastAI</b>\\nВыберите раздел:",
        "denied": "⛔ Этот раздел доступен только администратору бота.",
        "permission": "Доступ запрещён.",
        "grant_prompt": "👤 Отправьте Telegram ID пользователя или его @username.",
        "back": "⬅️ Панель администратора",
    },
    "en": {
        "title": "🛠 <b>RoastAI Admin Panel</b>\\nChoose a section:",
        "denied": "⛔ This section is only available to the bot administrator.",
        "permission": "Access denied.",
        "grant_prompt": "👤 Send the user's Telegram ID or @username.",
        "back": "⬅️ Admin panel",
    },
    "ar": {
        "title": "🛠 <b>لوحة إدارة RoastAI</b>\\nاختر قسمًا:",
        "denied": "⛔ هذا القسم متاح لمسؤول البوت فقط.",
        "permission": "تم رفض الوصول.",
        "grant_prompt": "👤 أرسل معرّف Telegram للمستخدم أو اسم المستخدم @username.",
        "back": "⬅️ لوحة الإدارة",
    },
    "ko": {
        "title": "🛠 <b>RoastAI 관리자 패널</b>\\n항목을 선택하세요:",
        "denied": "⛔ 이 메뉴는 봇 관리자만 사용할 수 있습니다.",
        "permission": "접근이 거부되었습니다.",
        "grant_prompt": "👤 사용자의 텔레그램 ID 또는 @username을 보내세요.",
        "back": "⬅️ 관리자 패널",
    },
    "zh": {
        "title": "🛠 <b>RoastAI 管理面板</b>\\n请选择一个栏目：",
        "denied": "⛔ 此栏目仅供机器人管理员使用。",
        "permission": "无权访问。",
        "grant_prompt": "👤 请发送用户的 Telegram ID 或 @username。",
        "back": "⬅️ 管理面板",
    },
}


def at(language, key):
    lang = language if language in ADMIN_TEXTS else "uz"
    return ADMIN_TEXTS[lang].get(key, ADMIN_TEXTS["uz"][key])




# Administrator bo‘limlari uchun ko‘p tilli matnlar
ADMIN_TEXTS["uz"].update({
    "stats": "📊 <b>Bot statistikasi</b>\nFoydalanuvchilar: {users}\nGuruhlar: {groups}",
    "plans": "📦 <b>Kunlik tarif limitlari</b>\nFREE: {free:,}\nPRO: {pro:,}\nPREMIUM: {premium:,}",
    "no_payments": "💳 Hozircha kutilayotgan to‘lovlar yo‘q.",
    "payments_title": "💳 <b>Kutilayotgan to‘lovlar:</b> {count}",
    "no_history": "📜 To‘lovlar tarixi hozircha bo‘sh.",
    "history_title": "📜 <b>Oxirgi to‘lovlar</b>",
    "no_logs": "🧾 Jurnal hozircha bo‘sh.",
    "logs_title": "🧾 <b>To‘lovlar jurnali</b>",
    "payment_user_rejected": '❌ №{payment_id} raqamli to‘lovingiz rad etildi. Aniqlik kiritish uchun administrator bilan bog‘laning.',
})
ADMIN_TEXTS["ru"].update({
    "stats": "📊 <b>Статистика бота</b>\nПользователи: {users}\nГруппы: {groups}",
    "plans": "📦 <b>Дневные лимиты тарифов</b>\nFREE: {free:,}\nPRO: {pro:,}\nPREMIUM: {premium:,}",
    "no_payments": "💳 Нет ожидающих платежей.",
    "payments_title": "💳 <b>Ожидающие платежи:</b> {count}",
    "no_history": "📜 История платежей пока пуста.",
    "history_title": "📜 <b>Последние платежи</b>",
    "no_logs": "🧾 Журнал пока пуст.",
    "logs_title": "🧾 <b>Журнал платежей</b>",
    "payment_user_rejected": '❌ Ваш платёж №{payment_id} отклонён. Обратитесь к администратору для уточнения.',
})
ADMIN_TEXTS["en"].update({
    "stats": "📊 <b>Bot statistics</b>\nUsers: {users}\nGroups: {groups}",
    "plans": "📦 <b>Daily plan limits</b>\nFREE: {free:,}\nPRO: {pro:,}\nPREMIUM: {premium:,}",
    "no_payments": "💳 There are no pending payments.",
    "payments_title": "💳 <b>Pending payments:</b> {count}",
    "no_history": "📜 Payment history is empty.",
    "history_title": "📜 <b>Recent payments</b>",
    "no_logs": "🧾 The log is empty.",
    "logs_title": "🧾 <b>Payment log</b>",
    "payment_user_rejected": '❌ Your payment №{payment_id} was rejected. Contact the administrator for clarification.',
})
ADMIN_TEXTS["ar"].update({
    "stats": "📊 <b>إحصائيات البوت</b>\nالمستخدمون: {users}\nالمجموعات: {groups}",
    "plans": "📦 <b>حدود الباقات اليومية</b>\nFREE: {free:,}\nPRO: {pro:,}\nPREMIUM: {premium:,}",
    "no_payments": "💳 لا توجد مدفوعات معلقة.",
    "payments_title": "💳 <b>المدفوعات المعلقة:</b> {count}",
    "no_history": "📜 سجل المدفوعات فارغ حاليًا.",
    "history_title": "📜 <b>أحدث المدفوعات</b>",
    "no_logs": "🧾 السجل فارغ حاليًا.",
    "logs_title": "🧾 <b>سجل المدفوعات</b>",
    "payment_user_rejected": '❌ تم رفض دفعتك رقم {payment_id}. يرجى التواصل مع المسؤول للاستفسار.',
})
ADMIN_TEXTS["ko"].update({
    "stats": "📊 <b>봇 통계</b>\n사용자: {users}\n그룹: {groups}",
    "plans": "📦 <b>일일 요금제 한도</b>\nFREE: {free:,}\nPRO: {pro:,}\nPREMIUM: {premium:,}",
    "no_payments": "💳 대기 중인 결제가 없습니다.",
    "payments_title": "💳 <b>대기 중인 결제:</b> {count}",
    "no_history": "📜 결제 내역이 비어 있습니다.",
    "history_title": "📜 <b>최근 결제</b>",
    "no_logs": "🧾 로그가 비어 있습니다.",
    "logs_title": "🧾 <b>결제 로그</b>",
    "payment_user_rejected": '❌ 결제 번호 {payment_id}가 거절되었습니다. 자세한 내용은 관리자에게 문의하세요.',
})
ADMIN_TEXTS["zh"].update({
    "stats": "📊 <b>机器人统计</b>\n用户：{users}\n群组：{groups}",
    "plans": "📦 <b>每日套餐限额</b>\nFREE: {free:,}\nPRO: {pro:,}\nPREMIUM: {premium:,}",
    "no_payments": "💳 暂无待处理付款。",
    "payments_title": "💳 <b>待处理付款：</b>{count}",
    "no_history": "📜 暂无付款记录。",
    "history_title": "📜 <b>最近付款</b>",
    "no_logs": "🧾 日志为空。",
    "logs_title": "🧾 <b>付款日志</b>",
    "payment_user_rejected": '❌ 您的付款编号 {payment_id} 已被拒绝。如需了解详情，请联系管理员。',
})


ADMIN_TEXTS["uz"].update({
    "payment_detail": '🧾 <b>To‘lov №{id}</b>\n👤 {username}\n🆔 ID: <code>{user_id}</code>\n📦 Mahsulot: {item}\n💰 Summa: {amount:,}\n📅 Sana: {date}',
    "username_missing": 'username yo‘q',
    "token_item": '🎟 {count:,} token',
    "plan_item": '⭐ {plan} tarifi'
})
ADMIN_TEXTS["ru"].update({
    "payment_detail": '🧾 <b>Платёж №{id}</b>\n👤 {username}\n🆔 ID: <code>{user_id}</code>\n📦 Товар: {item}\n💰 Сумма: {amount:,}\n📅 Дата: {date}',
    "username_missing": 'нет username',
    "token_item": '🎟 {count:,} токенов',
    "plan_item": '⭐ Тариф {plan}'
})
ADMIN_TEXTS["en"].update({
    "payment_detail": '🧾 <b>Payment №{id}</b>\n👤 {username}\n🆔 ID: <code>{user_id}</code>\n📦 Item: {item}\n💰 Amount: {amount:,}\n📅 Date: {date}',
    "username_missing": 'username unavailable',
    "token_item": '🎟 {count:,} tokens',
    "plan_item": '⭐ {plan} plan'
})
ADMIN_TEXTS["ar"].update({
    "payment_detail": '🧾 <b>الدفع رقم {id}</b>\n👤 {username}\n🆔 المعرّف: <code>{user_id}</code>\n📦 المنتج: {item}\n💰 المبلغ: {amount:,}\n📅 التاريخ: {date}',
    "username_missing": 'اسم المستخدم غير متوفر',
    "token_item": '🎟 {count:,} رمز',
    "plan_item": '⭐ باقة {plan}'
})
ADMIN_TEXTS["ko"].update({
    "payment_detail": '🧾 <b>결제 번호 {id}</b>\n👤 {username}\n🆔 ID: <code>{user_id}</code>\n📦 상품: {item}\n💰 금액: {amount:,}\n📅 날짜: {date}',
    "username_missing": '사용자 이름 없음',
    "token_item": '🎟 토큰 {count:,}개',
    "plan_item": '⭐ {plan} 요금제'
})
ADMIN_TEXTS["zh"].update({
    "payment_detail": '🧾 <b>付款编号 {id}</b>\n👤 {username}\n🆔 用户编号：<code>{user_id}</code>\n📦 商品：{item}\n💰 金额：{amount:,}\n📅 日期：{date}',
    "username_missing": '没有用户名',
    "token_item": '🎟 {count:,} 个代币',
    "plan_item": '⭐ {plan} 套餐'
})

ADMIN_TEXTS['uz'].update({
    'payment_confirm_detail': 'To‘lov №{id}\nFoydalanuvchi ID: <code>{user_id}</code>\nBerildi: {granted}\nSumma: {amount:,}',
    'payment_confirm_error': '❌ Tasdiqlab bo‘lmadi: {reason}',
    'granted_tokens': '{count:,} token',
    'granted_plan': '{plan} tarifi (30 kun)'
})
ADMIN_TEXTS['ru'].update({
    'payment_confirm_detail': 'Платёж №{id}\nID пользователя: <code>{user_id}</code>\nВыдано: {granted}\nСумма: {amount:,}',
    'payment_confirm_error': '❌ Не удалось подтвердить: {reason}',
    'granted_tokens': '{count:,} токенов',
    'granted_plan': 'Тариф {plan} (30 дней)'
})
ADMIN_TEXTS['en'].update({
    'payment_confirm_detail': 'Payment №{id}\nUser ID: <code>{user_id}</code>\nGranted: {granted}\nAmount: {amount:,}',
    'payment_confirm_error': '❌ Could not confirm: {reason}',
    'granted_tokens': '{count:,} tokens',
    'granted_plan': '{plan} plan (30 days)'
})
ADMIN_TEXTS['ar'].update({
    'payment_confirm_detail': 'الدفع رقم {id}\nمعرّف المستخدم: <code>{user_id}</code>\nتم منح: {granted}\nالمبلغ: {amount:,}',
    'payment_confirm_error': '❌ تعذّر التأكيد: {reason}',
    'granted_tokens': '{count:,} رمز',
    'granted_plan': 'باقة {plan} (30 يومًا)'
})
ADMIN_TEXTS['ko'].update({
    'payment_confirm_detail': '결제 번호 {id}\n사용자 ID: <code>{user_id}</code>\n지급 항목: {granted}\n금액: {amount:,}',
    'payment_confirm_error': '❌ 승인 실패: {reason}',
    'granted_tokens': '토큰 {count:,}개',
    'granted_plan': '{plan} 요금제 (30일)'
})
ADMIN_TEXTS['zh'].update({
    'payment_confirm_detail': '付款编号 {id}\n用户编号：<code>{user_id}</code>\n已发放：{granted}\n金额：{amount:,}',
    'payment_confirm_error': '❌ 确认失败：{reason}',
    'granted_tokens': '{count:,} 个代币',
    'granted_plan': '{plan} 套餐（30天）'
})

ADMIN_TEXTS["uz"].update({
    "user_missing": "❌ Foydalanuvchi bazadan topilmadi. U avval bot bilan muloqot qilgan bo‘lishi kerak.",
    "username_missing": "username yo‘q",
    "choose_plan": "Qaysi tarifni bermoqchisiz?",
    "grant_success": "✅ Foydalanuvchiga {plan} tarifi 30 kunga berildi.\n🆔 ID: <code>{user_id}</code>\n📅 Tugash sanasi: {date}",
    "bad_request": "Noto‘g‘ri so‘rov.",
    "plan_saved": "Tarif saqlandi.",
})
ADMIN_TEXTS["ru"].update({
    "user_missing": "❌ Пользователь не найден в базе. Сначала он должен взаимодействовать с ботом.",
    "username_missing": "нет username",
    "choose_plan": "Какой тариф вы хотите назначить?",
    "grant_success": "✅ Тариф {plan} назначен пользователю на 30 дней.\n🆔 ID: <code>{user_id}</code>\n📅 Дата окончания: {date}",
    "bad_request": "Некорректный запрос.",
    "plan_saved": "Тариф сохранён.",
})
ADMIN_TEXTS["en"].update({
    "user_missing": "❌ User not found in the database. They must interact with the bot first.",
    "username_missing": "no username",
    "choose_plan": "Which plan would you like to assign?",
    "grant_success": "✅ The {plan} plan has been assigned for 30 days.\n🆔 ID: <code>{user_id}</code>\n📅 Expiry date: {date}",
    "bad_request": "Invalid request.",
    "plan_saved": "Plan saved.",
})
ADMIN_TEXTS["ar"].update({
    "user_missing": "❌ لم يتم العثور على المستخدم في قاعدة البيانات. يجب أن يتفاعل مع البوت أولًا.",
    "username_missing": "لا يوجد اسم مستخدم",
    "choose_plan": "ما الباقة التي تريد تعيينها؟",
    "grant_success": "✅ تم تعيين باقة {plan} للمستخدم لمدة 30 يومًا.\n🆔 المعرّف: <code>{user_id}</code>\n📅 تاريخ الانتهاء: {date}",
    "bad_request": "طلب غير صالح.",
    "plan_saved": "تم حفظ الباقة.",
})
ADMIN_TEXTS["ko"].update({
    "user_missing": "❌ 데이터베이스에서 사용자를 찾을 수 없습니다. 먼저 봇과 대화해야 합니다.",
    "username_missing": "사용자 이름 없음",
    "choose_plan": "어떤 요금제를 지정하시겠습니까?",
    "grant_success": "✅ {plan} 요금제가 30일 동안 지정되었습니다.\n🆔 ID: <code>{user_id}</code>\n📅 만료일: {date}",
    "bad_request": "잘못된 요청입니다.",
    "plan_saved": "요금제가 저장되었습니다.",
})
ADMIN_TEXTS["zh"].update({
    "user_missing": "❌ 数据库中未找到该用户。用户需要先与机器人互动。",
    "username_missing": "没有用户名",
    "choose_plan": "要为用户开通哪个套餐？",
    "grant_success": "✅ 已为用户开通 {plan} 套餐，有效期 30 天。\n🆔 ID：<code>{user_id}</code>\n📅 到期日期：{date}",
    "bad_request": "请求无效。",
    "plan_saved": "套餐已保存。",
})


ADMIN_TEXTS["uz"].update({
    "pay_denied": 'Ruxsat yo‘q.',
    "payment_not_found": '❌ To‘lov topilmadi.',
    "payment_duplicate": '⚠️ Bu to‘lov avval qayta ishlangan.',
    "payment_bad_id": 'To‘lov raqami noto‘g‘ri.',
    "payment_confirmed": '✅ To‘lov tasdiqlandi.',
    "payment_rejected": '❌ To‘lov №{payment_id} rad etildi.',
    "payment_user_confirmed": '✅ To‘lovingiz tasdiqlandi.\nSizga berildi: {granted}',
})
ADMIN_TEXTS["ru"].update({
    "pay_denied": 'Нет доступа.',
    "payment_not_found": '❌ Платёж не найден.',
    "payment_duplicate": '⚠️ Этот платёж уже обработан.',
    "payment_bad_id": 'Неверный номер платежа.',
    "payment_confirmed": '✅ Платёж подтверждён.',
    "payment_rejected": '❌ Платёж №{payment_id} отклонён.',
    "payment_user_confirmed": '✅ Ваш платёж подтверждён.\nВам начислено: {granted}',
})
ADMIN_TEXTS["en"].update({
    "pay_denied": 'Access denied.',
    "payment_not_found": '❌ Payment not found.',
    "payment_duplicate": '⚠️ This payment has already been processed.',
    "payment_bad_id": 'Invalid payment number.',
    "payment_confirmed": '✅ Payment confirmed.',
    "payment_rejected": '❌ Payment №{payment_id} was rejected.',
    "payment_user_confirmed": '✅ Your payment was confirmed.\nGranted: {granted}',
})
ADMIN_TEXTS["ar"].update({
    "pay_denied": 'غير مسموح.',
    "payment_not_found": '❌ لم يتم العثور على الدفعة.',
    "payment_duplicate": '⚠️ تمت معالجة هذه الدفعة مسبقًا.',
    "payment_bad_id": 'رقم الدفعة غير صحيح.',
    "payment_confirmed": '✅ تم تأكيد الدفعة.',
    "payment_rejected": '❌ تم رفض الدفعة رقم {payment_id}.',
    "payment_user_confirmed": '✅ تم تأكيد دفعتك.\nتم منحك: {granted}',
})
ADMIN_TEXTS["ko"].update({
    "pay_denied": '권한이 없습니다.',
    "payment_not_found": '❌ 결제 내역을 찾을 수 없습니다.',
    "payment_duplicate": '⚠️ 이미 처리된 결제입니다.',
    "payment_bad_id": '잘못된 결제 번호입니다.',
    "payment_confirmed": '✅ 결제가 확인되었습니다.',
    "payment_rejected": '❌ 결제 번호 {payment_id}가 거절되었습니다.',
    "payment_user_confirmed": '✅ 결제가 확인되었습니다.\n지급 내용: {granted}',
})
ADMIN_TEXTS["zh"].update({
    "pay_denied": '没有权限。',
    "payment_not_found": '❌ 未找到付款记录。',
    "payment_duplicate": '⚠️ 该付款已处理。',
    "payment_bad_id": '付款编号无效。',
    "payment_confirmed": '✅ 付款已确认。',
    "payment_rejected": '❌ 付款编号 {payment_id} 已被拒绝。',
    "payment_user_confirmed": '✅ 您的付款已确认。\n已发放：{granted}',
})

def keyboard(language="uz"):
    labels = {
        "uz": ["📊 Statistika", "📦 Tarif limitlari", "👤 Foydalanuvchiga tarif berish", "💳 Kutilayotgan to‘lovlar", "📜 To‘lovlar tarixi", "🧾 Xatolar jurnali", "💰 To‘lov statistikasi"],
        "ru": ["📊 Статистика", "📦 Лимиты тарифов", "👤 Выдать тариф пользователю", "💳 Ожидающие платежи", "📜 История платежей", "🧾 Журнал ошибок", "💰 Статистика платежей"],
        "en": ["📊 Statistics", "📦 Plan limits", "👤 Grant a plan", "💳 Pending payments", "📜 Payment history", "🧾 Error log", "💰 Payment statistics"],
        "ar": ["📊 الإحصائيات", "📦 حدود الباقات", "👤 منح باقة لمستخدم", "💳 المدفوعات المعلقة", "📜 سجل المدفوعات", "🧾 سجل الأخطاء", "💰 إحصائيات الدفع"],
        "ko": ["📊 통계", "📦 요금제 한도", "👤 사용자에게 요금제 부여", "💳 대기 중인 결제", "📜 결제 내역", "🧾 오류 기록", "💰 결제 통계"],
        "zh": ["📊 统计", "📦 套餐限制", "👤 为用户开通套餐", "💳 待处理付款", "📜 付款记录", "🧾 错误日志", "💰 付款统计"],
    }
    lang = language if language in labels else "uz"
    keys = ["admin:stats", "admin:plans", "admin:grant", "admin:payments", "admin:history", "admin:logs", "admin:paymentstats"]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=key)]
        for label, key in zip(labels[lang], keys)
    ])

def payment_keyboard(payment_id, language="uz"):
    labels = {
        "uz": ("✅ Tasdiqlash", "❌ Rad etish"),
        "ru": ("✅ Подтвердить", "❌ Отклонить"),
        "en": ("✅ Confirm", "❌ Reject"),
        "ar": ("✅ تأكيد", "❌ رفض"),
        "ko": ("✅ 승인", "❌ 거절"),
        "zh": ("✅ 确认", "❌ 拒绝"),
    }
    confirm, reject = labels.get(language, labels["uz"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=confirm,
                callback_data=f"admin:payconfirm:{payment_id}"
            ),
            InlineKeyboardButton(
                text=reject,
                callback_data=f"admin:payreject:{payment_id}"
            ),
        ]
    ])


def admin_only(user_id):
    return config.is_admin(user_id)


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not message.from_user:
        return

    language = await admin_language(message.from_user.id)

    if not admin_only(message.from_user.id):
        await message.answer(at(language, "denied"))
        return

    await message.answer(
        at(language, "title"),
        reply_markup=keyboard(language)
    )

@router.callback_query(lambda c: c.data in (
    "admin:stats", "admin:plans", "admin:grant",
    "admin:payments", "admin:history", "admin:logs",
    "admin:paymentstats",
))
async def admin_action(callback: CallbackQuery):
    language = await admin_language(callback.from_user.id)
    if not admin_only(callback.from_user.id):
        await callback.answer(at(language, "permission"), show_alert=True)
        return

    if callback.data == "admin:grant":
        pending_grant.add(callback.from_user.id)
        await callback.message.answer(
            at(language, "grant_prompt")
        )
        await callback.answer()
        return

    if callback.data == "admin:stats":
        users, groups = await db.get_stats()
        text = (
            at(language, "stats").format(users=users, groups=groups)
        )

    elif callback.data == "admin:plans":
        text = (
            at(language, "plans").format(free=config.FREE_DAILY_TOKENS, pro=config.PRO_DAILY_TOKENS, premium=config.PREMIUM_DAILY_TOKENS)
        )

    elif callback.data == "admin:payments":
        payments = await db.get_pending_payments(20)
        await callback.answer()

        if not payments:
            await callback.message.answer(at(language, "no_payments"))
            return

        await callback.message.answer(
            at(language, "payments_title").format(count=len(payments))
        )

        for p in payments:
            username = (
                f"@{p['username']}"
                if p["username"]
                else at(language, "username_missing")
            )
            payment_type = p["payment_type"]
            item = (
                at(language, "token_item").format(
                    count=int(p["package_tokens"] or 0)
                )
                if payment_type == "tokens"
                else at(language, "plan_item").format(
                    plan=str(p["plan"]).upper()
                )
            )
            text = at(language, "payment_detail").format(
                id=p["id"],
                username=username,
                user_id=p["user_id"],
                item=item,
                amount=int(p["amount"]),
                date=p["created_at"],
            )
            await callback.message.answer(
                text,
                reply_markup=payment_keyboard(p["id"], language)
            )
        return

    elif callback.data == "admin:history":
        rows = await db.get_payment_history(limit=15)
        await callback.answer()

        if not rows:
            await callback.message.answer(at(language, "no_history"))
            return

        lines = [at(language, "history_title")]
        for p in rows:
            lines.append(
                f"\n№{p['id']} | ID: {p['user_id']}\n"
                f"Summa: {int(p['amount']):,} | Holat: {p['status']}\n"
                f"Sana: {p['created_at']}"
            )

        text = "\n".join(lines)
        for start in range(0, len(text), 3500):
            await callback.message.answer(text[start:start + 3500])
        return

    elif callback.data == "admin:logs":
        rows = await db.get_payment_logs(limit=15)
        await callback.answer()

        if not rows:
            await callback.message.answer(at(language, "no_logs"))
            return

        lines = [at(language, "logs_title")]
        for row in rows:
            details = str(row["details"] or "")[:250]
            lines.append(
                f"\n#{row['id']} | To‘lov: {row['payment_id']}\n"
                f"Foydalanuvchi ID: {row['user_id']}\n"
                f"Amal: {row['action']}\n"
                f"Ma’lumot: {details}\n"
                f"Sana: {row['created_at']}"
            )

        text = "\n".join(lines)
        for start in range(0, len(text), 3500):
            await callback.message.answer(text[start:start + 3500])
        return

    else:
        stats = await db.get_payment_stats()
        text = (
            "💰 <b>To‘lov statistikasi</b>\n"
            f"Jami to‘lovlar: {stats['total']}\n"
            f"⏳ Kutilmoqda: {stats['pending']}\n"
            f"✅ Tasdiqlangan: {stats['paid']}\n"
            f"❌ Rad etilgan: {stats['rejected']}\n"
            f"💵 Jami tushum: {stats['revenue']:,}"
        )

    await callback.message.answer(text, reply_markup=keyboard())
    await callback.answer()


@router.message(lambda m: m.from_user and m.from_user.id in pending_grant)
async def admin_grant_user(message: Message):
    if not message.from_user or message.from_user.id not in pending_grant:
        return

    language = await admin_language(message.from_user.id)
    query = (message.text or "").strip()
    if not query or query.startswith("/"):
        return

    pending_grant.discard(message.from_user.id)
    user = await db.find_user(query)

    if not user:
        await message.answer(at(language, "user_missing"))
        return

    user_id = user["user_id"]
    username = f"@{user['username']}" if user["username"] else at(language, "username_missing")

    plan_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ PRO", callback_data=f"admin:setplan:pro:{user_id}"),
            InlineKeyboardButton(text="💎 PREMIUM", callback_data=f"admin:setplan:premium:{user_id}"),
        ],
        [InlineKeyboardButton(text=at(language, "back"), callback_data="admin:back")],
    ])

    await message.answer(
        f"👤 Foydalanuvchi: {username}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        + at(language, "choose_plan"),
        reply_markup=plan_keyboard
    )


@router.callback_query(lambda c: c.data and c.data.startswith("admin:setplan:"))
async def admin_set_plan(callback: CallbackQuery):
    language = await admin_language(callback.from_user.id)
    if not admin_only(callback.from_user.id):
        await callback.answer(at(language, "permission"), show_alert=True)
        return

    try:
        _, _, plan, user_id = callback.data.split(":")
        user_id = int(user_id)
        if plan not in ("pro", "premium"):
            raise ValueError
    except (ValueError, AttributeError):
        await callback.answer(at(language, "bad_request"), show_alert=True)
        return

    expires_at = (datetime.now() + timedelta(days=30)).isoformat(timespec="seconds")
    await db.set_user_plan(user_id, plan, expires_at)

    await callback.message.answer(
        at(language, "grant_success").format(plan=plan.upper(), user_id=user_id, date=expires_at[:10])
    )
    await callback.answer(at(language, "plan_saved"))


@router.callback_query(lambda c: c.data and c.data.startswith("admin:payconfirm:"))
async def admin_confirm_payment(callback: CallbackQuery):
    language = await admin_language(callback.from_user.id)
    if not admin_only(callback.from_user.id):
        await callback.answer(at(language, "pay_denied"), show_alert=True)
        return

    try:
        payment_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer(at(language, "payment_bad_id"), show_alert=True)
        return

    result = await db.confirm_payment_once(payment_id, callback.from_user.id)

    if not result["ok"]:
        reason = result.get("reason")
        text = (
            at(language, "payment_not_found")
            if reason == "not_found"
            else at(language, "payment_duplicate")
            if reason == "already_processed"
            else at(language, "payment_confirm_error").format(reason=reason)
        )
        await callback.answer(text, show_alert=True)
        return

    user_id = result["user_id"]
    if result["payment_type"] == "tokens":
        granted = at(language, "granted_tokens").format(count=int(result["tokens"]))
    else:
        granted = at(language, "granted_plan").format(plan=result["plan"].upper())

    await callback.message.answer(
        f"{at(language, 'payment_confirmed')}\\n"
        + at(language, "payment_confirm_detail").format(
            id=payment_id,
            user_id=user_id,
            granted=granted,
            amount=int(result["amount"]),
        )
    )

    try:
        await callback.bot.send_message(
            user_id,
            at(language, "payment_user_confirmed").format(granted=granted)
        )
    except Exception:
        pass

    await callback.answer(at(language, "payment_confirmed"))


@router.callback_query(lambda c: c.data and c.data.startswith("admin:payreject:"))
async def admin_reject_payment(callback: CallbackQuery):
    language = await admin_language(callback.from_user.id)
    if not admin_only(callback.from_user.id):
        await callback.answer(at(language, "pay_denied"), show_alert=True)
        return

    try:
        payment_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer(at(language, "payment_bad_id"), show_alert=True)
        return

    ok = await db.reject_payment(
        payment_id,
        callback.from_user.id,
        "Administrator tomonidan rad etildi"
    )

    if not ok:
        await callback.answer(
            at(language, "payment_duplicate"),
            show_alert=True
        )
        return

    payment = await db.get_payment(payment_id)
    await callback.message.answer(
        at(language, "payment_rejected").format(payment_id=payment_id)
    )

    if payment:
        try:
            await callback.bot.send_message(
                int(payment["user_id"]),
                at(language, "payment_user_rejected").format(payment_id=payment_id)
            )
        except Exception:
            pass

    await callback.answer(at(language, "payment_rejected").format(payment_id=payment_id))


@router.callback_query(lambda c: c.data == "admin:back")
async def admin_back(callback: CallbackQuery):
    language = await admin_language(callback.from_user.id)
    if not admin_only(callback.from_user.id):
        await callback.answer(at(language, "permission"), show_alert=True)
        return
    await callback.message.answer(
        at(language, "title"),
        reply_markup=keyboard(language)
    )
    await callback.answer()
