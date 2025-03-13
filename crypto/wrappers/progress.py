from tqdm import tqdm

class ProgressBar:
    """
    Класс для работы с прогресс-баром
    """
    
    @staticmethod
    def create(total: int, desc: str, unit: str = "%", unit_scale: bool = False) -> tqdm:
        """
        Создает прогресс-бар
        
        Args:
            total: Общее количество итераций
            desc: Описание прогресс-бара
            unit: Единица измерения (по умолчанию %)
            unit_scale: Масштабирование единиц
            
        Returns:
            tqdm: Объект прогресс-бара
        """
        return tqdm(total=total, desc=desc, unit=unit, unit_scale=unit_scale)
    
    @staticmethod
    def update_percentage(pbar: tqdm, current: int, total: int) -> None:
        """
        Обновляет прогресс-бар в процентах
        
        Args:
            pbar: Объект прогресс-бара
            current: Текущее значение
            total: Общее значение
        """
        progress_pct = min(current / total * 100, 100) if total > 0 else 100
        pbar.update(progress_pct - pbar.n) 