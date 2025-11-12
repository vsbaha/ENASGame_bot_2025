"""
Управление сетками турниров
"""
from .bracket_generator import router as bracket_generator_router
from .bracket_editor import router as bracket_editor_router
from aiogram import Router

# Объединяем роутеры
bracket_router = Router()
bracket_router.include_router(bracket_generator_router)
bracket_router.include_router(bracket_editor_router)

__all__ = ['bracket_router']
