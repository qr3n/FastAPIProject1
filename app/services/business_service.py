from typing import List
from shared.models.business import Business
from shared.models.user import User
from app.schemas.business import BusinessCreateSchema, BusinessUpdateSchema
from app.exceptions.business_exceptions import (
    BusinessNotFoundError,
    BusinessAccessDeniedError,
    InvalidTelegramTokenError
)
from app.services.bot_manager_service import bot_manager
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

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
        # Проверяем валидность токена бота
        bot_info = await bot_manager.verify_bot_token(business_data.telegram_bot_token)

        if not bot_info:
            raise InvalidTelegramTokenError("Invalid Telegram bot token")

        logger.info(f"Bot verified: @{bot_info.get('username')} ({bot_info.get('first_name')})")

        # Создаём бизнес
        business = await Business.create(
            owner=owner,
            name=business_data.name,
            description=business_data.description,
            business_type=business_data.business_type,
            telegram_bot_token=business_data.telegram_bot_token
        )

        # Регистрируем webhook для бота
        webhook_success = await bot_manager.register_bot_webhook(
            bot_token=business.telegram_bot_token,
            business_id=str(business.id)
        )

        if webhook_success:
            logger.info(f"✅ Bot registered for business '{business.name}' (@{bot_info.get('username')})")
        else:
            logger.error(f"❌ Failed to register webhook for business '{business.name}'")
            await business.update_from_dict({"is_active": False}).save()
            logger.warning(f"Business created but bot is inactive due to webhook registration failure")

        return business

    @staticmethod
    async def get_business_by_id(
            business_id: str,
            include_tables: bool = False,
            include_dishes: bool = False
    ) -> Business:
        """
        Get business by ID.

        Args:
            business_id: Business UUID
            include_tables: Prefetch tables data
            include_dishes: Prefetch dishes data

        Returns:
            Business instance

        Raises:
            BusinessNotFoundError: If business doesn't exist
        """
        query = Business.filter(id=business_id)

        # Prefetch related data if requested
        if include_tables:
            query = query.prefetch_related('tables')
        if include_dishes:
            query = query.prefetch_related('dishes')

        business = await query.first()

        if not business:
            raise BusinessNotFoundError(business_id)

        return business

    @staticmethod
    async def get_user_businesses(
            user: User,
            include_tables: bool = False,
            include_dishes: bool = False
    ) -> List[Business]:
        """
        Get all businesses owned by user.

        Args:
            user: User instance
            include_tables: Prefetch tables data
            include_dishes: Prefetch dishes data

        Returns:
            List of user's businesses
        """
        query = Business.filter(owner=user)

        # Prefetch related data if requested
        if include_tables:
            query = query.prefetch_related('tables')
        if include_dishes:
            query = query.prefetch_related('dishes')

        return await query.all()

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
            InvalidTelegramTokenError: If new bot token is invalid
        """
        business = await BusinessService.get_business_by_id(business_id)

        if business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        update_fields = {}

        if business_data.name is not None:
            update_fields['name'] = business_data.name

        if business_data.description is not None:
            update_fields['description'] = business_data.description

        # Управление активностью бота
        if business_data.is_active is not None:
            if business_data.is_active and not business.is_active:
                # Активируем бота
                logger.info(f"Activating bot for business '{business.name}'")
                success = await bot_manager.register_bot_webhook(
                    bot_token=business.telegram_bot_token,
                    business_id=str(business.id)
                )
                if success:
                    update_fields['is_active'] = True
                else:
                    logger.error("Failed to activate bot")

            elif not business_data.is_active and business.is_active:
                # Деактивируем бота
                logger.info(f"Deactivating bot for business '{business.name}'")
                await bot_manager.unregister_bot_webhook(
                    bot_token=business.telegram_bot_token,
                    business_id=str(business.id)
                )
                update_fields['is_active'] = False

        if update_fields:
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

        logger.info(f"Deleting business '{business.name}' and its bot")

        # Удаляем webhook бота
        await bot_manager.unregister_bot_webhook(
            bot_token=business.telegram_bot_token,
            business_id=str(business.id)
        )

        # Удаляем бизнес
        await business.delete()

        logger.info(f"✅ Business '{business.name}' deleted successfully")

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

    @staticmethod
    async def get_bot_status(business_id: str, user: User) -> dict:
        """
        Get current bot status and info.

        Args:
            business_id: Business UUID
            user: User making the request

        Returns:
            Dict with bot status information
        """
        business = await BusinessService.get_business_by_id(business_id)

        if business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        bot_info = await bot_manager.get_bot_info(business.telegram_bot_token)

        return {
            "business_id": str(business.id),
            "business_name": business.name,
            "is_active": business.is_active,
            "bot_info": bot_info,
            "bot_username": bot_info.get("username") if bot_info else None
        }

    @staticmethod
    async def get_business_stats(business_id: str, user: User) -> dict:
        """
        Get business statistics including tables and dishes info.

        Args:
            business_id: Business UUID
            user: User making the request

        Returns:
            Dict with business statistics
        """
        from shared.models.table import Table, TableStatus
        from shared.models.dish import Dish

        business = await BusinessService.get_business_by_id(business_id)

        if business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        # Статистика столиков
        total_tables = await Table.filter(business=business).count()
        active_tables = await Table.filter(business=business, is_active=True).count()
        available_tables = await Table.filter(
            business=business,
            status=TableStatus.AVAILABLE,
            is_active=True
        ).count()

        # Статистика блюд
        total_dishes = await Dish.filter(business=business).count()
        available_dishes = await Dish.filter(business=business, is_available=True).count()

        return {
            "business_id": str(business.id),
            "business_name": business.name,
            "tables": {
                "total": total_tables,
                "active": active_tables,
                "available": available_tables
            },
            "dishes": {
                "total": total_dishes,
                "available": available_dishes
            }
        }