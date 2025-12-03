# app/services/business_service.py
from typing import List
from app.models.business import Business
from app.models.user import User
from app.schemas.business import BusinessCreateSchema, BusinessUpdateSchema
from app.exceptions.business_exceptions import (
    BusinessNotFoundError,
    BusinessAccessDeniedError,
    InvalidTelegramTokenError
)
from app.services.bot_manager_service import bot_manager
import logging

logger = logging.getLogger(__name__)


class BusinessService:
    """Service for managing businesses."""

    @staticmethod
    async def create_business(
            business_data: BusinessCreateSchema,
            owner: User
    ) -> Business:
        """
        Create a new business with Telegram bot.

        Args:
            business_data: Business creation data
            owner: Business owner

        Returns:
            Created business instance

        Raises:
            InvalidTelegramTokenError: If bot token is invalid
        """
        # 1. Проверяем валидность токена бота
        bot_info = await bot_manager.verify_bot_token(business_data.telegram_bot_token)

        if not bot_info:
            raise InvalidTelegramTokenError("Invalid Telegram bot token")

        logger.info(f"Bot verified: @{bot_info.get('username')}")

        # 2. Создаем бизнес в БД
        business = await Business.create(
            owner=owner,
            name=business_data.name,
            description=business_data.description,
            business_type=business_data.business_type,
            telegram_bot_token=business_data.telegram_bot_token
        )

        logger.info(f"Business created: {business.id} - {business.name}")

        # 3. Регистрируем webhook для бота
        webhook_registered = await bot_manager.register_bot_webhook(
            bot_token=business_data.telegram_bot_token,
            business_id=str(business.id)
        )

        if not webhook_registered:
            logger.error(f"Failed to register webhook for business {business.id}")
            # Можно либо откатить создание бизнеса, либо пометить как неактивный
            await business.update_from_dict({"is_active": False}).save()
            raise InvalidTelegramTokenError("Failed to register bot webhook")

        logger.info(f"✅ Bot launched for business '{business.name}' (@{bot_info.get('username')})")

        return business

    @staticmethod
    async def get_business_by_id(business_id: str) -> Business:
        """
        Get business by ID.

        Args:
            business_id: Business UUID

        Returns:
            Business instance

        Raises:
            BusinessNotFoundError: If business doesn't exist
        """
        business = await Business.get_or_none(id=business_id)

        if not business:
            raise BusinessNotFoundError(business_id)

        return business

    @staticmethod
    async def get_user_businesses(user: User) -> List[Business]:
        """
        Get all businesses owned by user.

        Args:
            user: User instance

        Returns:
            List of user's businesses
        """
        return await Business.filter(owner=user).all()

    @staticmethod
    async def update_business(
            business_id: str,
            business_data: BusinessUpdateSchema,
            user: User
    ) -> Business:
        """
        Update a business.

        Args:
            business_id: Business UUID
            business_data: Updated business data
            user: User making the request

        Returns:
            Updated business instance

        Raises:
            BusinessNotFoundError: If business doesn't exist
            BusinessAccessDeniedError: If user doesn't own the business
        """
        business = await BusinessService.get_business_by_id(business_id)

        if business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        update_fields = {}

        if business_data.name is not None:
            update_fields['name'] = business_data.name

        if business_data.description is not None:
            update_fields['description'] = business_data.description

        if business_data.business_type is not None:
            update_fields['business_type'] = business_data.business_type

        # Обработка обновления токена бота
        if business_data.telegram_bot_token is not None:
            # Проверяем новый токен
            bot_info = await bot_manager.verify_bot_token(business_data.telegram_bot_token)

            if not bot_info:
                raise InvalidTelegramTokenError("Invalid Telegram bot token")

            # Обновляем webhook (удаляем старый, регистрируем новый)
            old_token = business.telegram_bot_token
            new_token = business_data.telegram_bot_token

            if old_token != new_token:
                success = await bot_manager.update_bot_token(
                    old_token=old_token,
                    new_token=new_token,
                    business_id=str(business.id)
                )

                if success:
                    update_fields['telegram_bot_token'] = new_token
                    logger.info(f"Bot token updated for business {business.id}")
                else:
                    raise InvalidTelegramTokenError("Failed to update bot webhook")

        if business_data.is_active is not None:
            update_fields['is_active'] = business_data.is_active

            # Если бизнес деактивируется - удаляем webhook
            if not business_data.is_active:
                await bot_manager.unregister_bot_webhook(
                    bot_token=business.telegram_bot_token,
                    business_id=str(business.id)
                )
                logger.info(f"Bot deactivated for business {business.id}")

            # Если активируется - регистрируем webhook
            elif business_data.is_active and not business.is_active:
                await bot_manager.register_bot_webhook(
                    bot_token=business.telegram_bot_token,
                    business_id=str(business.id)
                )
                logger.info(f"Bot activated for business {business.id}")

        await business.update_from_dict(update_fields).save()
        await business.refresh_from_db()

        return business

    @staticmethod
    async def delete_business(business_id: str, user: User) -> None:
        """
        Delete a business.

        Args:
            business_id: Business UUID
            user: User making the request

        Raises:
            BusinessNotFoundError: If business doesn't exist
            BusinessAccessDeniedError: If user doesn't own the business
        """
        business = await BusinessService.get_business_by_id(business_id)

        if business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        # Удаляем webhook бота
        await bot_manager.unregister_bot_webhook(
            bot_token=business.telegram_bot_token,
            business_id=str(business.id)
        )

        logger.info(f"Bot deleted for business '{business.name}'")

        await business.delete()

    @staticmethod
    def verify_business_access(business: Business, user: User) -> None:
        """
        Verify user has access to business.

        Args:
            business: Business to check
            user: User to verify

        Raises:
            BusinessAccessDeniedError: If user doesn't own the business
        """
        if business.owner_id != user.id:
            raise BusinessAccessDeniedError()