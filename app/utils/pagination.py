"""
Утилиты для пагинации.
"""
from typing import List, Any, Optional


class Paginator:
    """
    Класс для пагинации данных.
    """
    
    def __init__(self, items: List[Any], page: int, per_page: int, total: int):
        """
        Инициализация пагинатора.
        
        Args:
            items: Список элементов на текущей странице
            page: Номер текущей страницы
            per_page: Количество элементов на странице
            total: Общее количество элементов
        """
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = (total + per_page - 1) // per_page if total > 0 else 0
    
    @property
    def has_prev(self) -> bool:
        """Есть ли предыдущая страница."""
        return self.page > 1
    
    @property
    def has_next(self) -> bool:
        """Есть ли следующая страница."""
        return self.page < self.pages
    
    @property
    def prev_page(self) -> Optional[int]:
        """Номер предыдущей страницы."""
        return self.page - 1 if self.has_prev else None
    
    @property
    def next_page(self) -> Optional[int]:
        """Номер следующей страницы."""
        return self.page + 1 if self.has_next else None
    
    def iter_pages(self, left_edge: int = 2, right_edge: int = 2, left_current: int = 2, right_current: int = 2) -> List[Optional[int]]:
        """
        Генерирует список номеров страниц для отображения.
        
        Args:
            left_edge: Количество страниц слева от начала
            right_edge: Количество страниц справа от конца
            left_current: Количество страниц слева от текущей
            right_current: Количество страниц справа от текущей
            
        Returns:
            Список номеров страниц (None означает пропуск)
        """
        last = self.pages
        pages = []
        
        # Левая граница
        for i in range(1, min(left_edge + 1, last + 1)):
            pages.append(i)
        
        # Пропуск после левой границы
        if left_edge < self.page - left_current - 1:
            pages.append(None)
        
        # Страницы вокруг текущей
        for i in range(max(1, self.page - left_current), min(self.page + right_current + 1, last + 1)):
            if i not in pages:
                pages.append(i)
        
        # Пропуск перед правой границей
        if self.page + right_current < last - right_edge:
            pages.append(None)
        
        # Правая граница
        for i in range(max(1, last - right_edge + 1), last + 1):
            if i not in pages:
                pages.append(i)
        
        return pages
    
    def to_dict(self) -> dict:
        """
        Преобразует пагинатор в словарь.
        
        Returns:
            Словарь с данными пагинации
        """
        return {
            'items': self.items,
            'page': self.page,
            'per_page': self.per_page,
            'total': self.total,
            'pages': self.pages,
            'has_prev': self.has_prev,
            'has_next': self.has_next,
            'prev_page': self.prev_page,
            'next_page': self.next_page
        }
