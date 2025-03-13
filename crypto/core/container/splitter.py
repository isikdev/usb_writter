import os
import random
import math
import glob
import hashlib
from typing import List
from crypto.wrappers.logging import logging
from crypto.constants import Msg, Def_val

class ContainerSplitter:
    def __init__(self, seed: str = None, min_chunk_ratio: float = Def_val.min_chunk_ratio):
        self.seed = seed
        self.min_chunk_ratio = min_chunk_ratio
        self._original_seed_state = random.getstate() if seed else None
        if seed:
            random.seed(seed)

    def _generate_random_extension(self) -> str:
        """Генерирует случайное расширение файла для маскировки частей контейнера"""
        extensions = ['jpg']  # можно расширить: ['jpg', 'png', 'mp4', 'mov', 'pdf', 'doc']
        return random.choice(extensions)

    def _generate_chunk_name(self, base_path: str, index: int, subindex: int = None) -> str:
        """Генерирует детерминированное случайное имя файла с использованием seed"""
        if not self.seed:
            return base_path
        
        # Сохраняем исходное состояние random
        original_state = random.getstate()
        
        # Генерируем компоненты имени с использованием seed-based рандомизации
        random.seed(f"{self.seed}-{index}-{subindex}")
        random_chars = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=4))
        extension = self._generate_random_extension()
        
        # Восстанавливаем исходное состояние random
        random.setstate(original_state)
        
        return f"{self.seed}-{index}-{subindex}-{random_chars}.{extension}"

    def _get_random_chunk_size(self, max_size: int, piece_size: int, chunk_index: int) -> int:
        """Генерирует случайный размер куска между min_ratio и максимальным размером piece_size"""
        if self.seed:
            chunk_seed = f"{self.seed}-{piece_size}-{chunk_index}"
            random.seed(chunk_seed)
        
        # Вычисляем минимальный размер на основе piece_size, а не оставшегося размера
        min_size = int(piece_size * self.min_chunk_ratio)
        
        # Используем бета-распределение между min_size и max_size
        ratio = random.betavariate(0.8, 0.8)
        size = min_size + int((max_size - min_size) * ratio)
        
        # Добавляем небольшой джиттер, сохраняя минимальный размер
        jitter = random.uniform(1.0, 1.05)  # Только положительный джиттер
        size = int(size * jitter)
        
        # Добавляем небольшое простое смещение, убеждаясь, что не опускаемся ниже min_size
        prime_offset = random.choice([0, 311, 733])  # Только положительные смещения
        size = min(max_size, size + prime_offset)
        
        if self.seed:
            random.setstate(self._original_seed_state)
        
        return size

    def _split_file(self, file_path: str, index: int, piece_size: int) -> List[str]:
        """Разделяет файл на куски случайного размера с использованием seed-based рандомизации"""
        logging.info(f"🔵 Начинаю разделение {file_path} (индекс {index})")
        logging.debug(f"Начальные параметры - piece_size: {piece_size}, seed: {self.seed}")
        
        if not os.path.exists(file_path):
            logging.error(f"🚨 Файл не существует: {file_path}")
            return []
            
        file_size = os.path.getsize(file_path)
        logging.info(f"📁 Размер файла: {file_size} байт")
        directory = os.path.dirname(file_path)
        chunks = []
        
        logging.debug(f"Размер файла: {file_size}, директория: {directory}")
        
        estimated_total_chunks = max(1, math.ceil(file_size / (piece_size * self.min_chunk_ratio)))
        logging.info(f"📈 Примерное количество кусков: {estimated_total_chunks} на основе размера куска {piece_size} байт")
        
        with open(file_path, 'rb') as f:
            position = 0
            chunk_index = 0
            
            while position < file_size:
                remaining = file_size - position
                max_possible = min(piece_size, remaining)
                
                # Получаем случайный размер куска
                chunk_size = self._get_random_chunk_size(
                    max_size=max_possible,
                    piece_size=piece_size,
                    chunk_index=chunk_index + index * 1000
                )
                logging.debug(f"🔢🔢 Размер куска {chunk_index + 1}: {chunk_size} байт")
                
                # Убеждаемся, что не превышаем оставшиеся байты
                chunk_size = min(chunk_size, remaining)
                chunk_data = f.read(chunk_size)
                
                chunk_name = self._generate_chunk_name(file_path, index, chunk_index)
                chunk_path = os.path.join(directory, chunk_name)
                logging.debug(f"Запись куска в: {chunk_path}")
                
                with open(chunk_path, 'wb') as chunk_file:
                    chunk_file.write(chunk_data)
                    logging.debug(f"✍️ Записан кусок {chunk_index + 1} ({len(chunk_data)} байт) в {chunk_path}")
                
                # После записи каждого куска
                actual_size = os.path.getsize(chunk_path)
                if actual_size == len(chunk_data):
                    logging.debug(f"✅ Размер куска проверен: {actual_size} байт")
                else:
                    logging.error(f"🚨 Несоответствие размера куска! Ожидалось {len(chunk_data)}, получено {actual_size}")
                
                chunks.append(chunk_path)
                position += chunk_size
                chunk_number = chunk_index + 1  # Нумерация с 1 для отображения пользователю
                logging.debug(f"🔢 Обработка куска {chunk_number}/{estimated_total_chunks}")
                progress_pct = min(position / file_size * 100, 100)  # Ограничиваем 100%
                logging.info(f"📊 Прогресс файла: {progress_pct:.1f}% - Кусок {chunk_number}")
                chunk_index += 1
        
        # Удаляем исходный файл после разделения
        logging.debug(f"Удаление исходного файла: {file_path}")
        os.remove(file_path)
        chunk_count = chunk_index
        plural = "кусок" if chunk_count == 1 else "кусков"
        logging.info(f"✅ Успешно разделен {file_path} на {chunk_count} {plural}")
        logging.debug(f"🔍 Общий исходный размер: {file_size} байт")
        logging.debug(f"🔍 Общий размер кусков: {sum(os.path.getsize(c) for c in chunks)} байт")
        return chunks

    def split_container(self, container_path: str, piece_size: int) -> List[str]:
        """Разделяет контейнер на куски случайного размера"""
        if not self.seed:
            logging.error("Не указан seed для разделения контейнера")
            return []
            
        # Преобразуем в абсолютный путь и нормализуем
        container_path = os.path.abspath(container_path)
        directory = os.path.dirname(container_path)
        if not directory:
            directory = '.'
            
        # Проверяем наличие существующих кусков с использованием seed-based шаблона
        if glob.glob(os.path.join(directory, f"{self.seed}-*")):
            logging.error(f"🚨 Найдены существующие куски для seed '{self.seed}'. Очистите предыдущие куски или используйте новый seed.")
            return []
            
        # Убеждаемся, что директория существует
        os.makedirs(directory, exist_ok=True)
            
        # Проверяем существование контейнера
        if not os.path.exists(container_path):
            logging.error(f"🚨 Контейнер не существует: {container_path}")
            return []
        
        try:
            chunks = self._split_file(container_path, 0, piece_size)
            logging.info(f"Контейнер {os.path.basename(container_path)} разделен на {len(chunks)} частей")
            return chunks
        except Exception as e:
            logging.error(f"Ошибка при разделении контейнера {container_path}: {str(e)}")
            return []

class ContainerReconstructor:
    def __init__(self, seed: str = None):
        self.seed = seed

    def _reconstruct_file(self, chunks: List[str], output_path: str) -> bool:
        """Восстанавливает файл из его кусков"""
        logging.info(f"🔵 Начинаю восстановление {output_path}")
        logging.debug(f"Кусков для обработки: {len(chunks)}")
        
        try:
            total_written = 0
            with open(output_path, 'wb') as out_file:
                for i, chunk_path in enumerate(chunks):
                    logging.debug(f"📥 Обработка куска {i+1}/{len(chunks)}: {chunk_path}")
                    
                    if not os.path.exists(chunk_path):
                        logging.error(f"🚨 Отсутствует кусок: {chunk_path}")
                        return False
                        
                    chunk_size = os.path.getsize(chunk_path)
                    logging.debug(f"📦 Размер куска: {chunk_size} байт")
                    
                    with open(chunk_path, 'rb') as chunk_file:
                        chunk_data = chunk_file.read()
                        out_file.write(chunk_data)
                        total_written += len(chunk_data)
                        logging.debug(f"✍️ Записано {len(chunk_data)} байт (всего: {total_written}) в куске {i+1}")
                    
                    # Проверяем инкрементальную запись
                    current_size = os.path.getsize(output_path)
                    if current_size != total_written:
                        logging.error(f"🚨 Несоответствие размера после куска {i+1}! {current_size} vs {total_written}")
                        return False
                    
                    # Удаляем кусок после успешной записи
                    logging.debug(f"🗑️ Удаление куска: {chunk_path}")
                    os.remove(chunk_path)
            
            logging.info(f"✅ Успешно восстановлен {output_path} ({total_written} байт)")
            return True
        except Exception as e:
            logging.error(f"🚨 Восстановление не удалось: {str(e)}")
            return False

    def restore_container(self, directory: str, output_path: str) -> bool:
        """Восстанавливает контейнер из кусков"""
        logging.info(f"🔄 Начинаю восстановление контейнера в {directory}")
        
        if not self.seed:
            logging.error("Не указан seed для восстановления контейнера")
            return False
        
        # Группируем куски и вычисляем размеры
        chunks = []
        for chunk in glob.glob(os.path.join(directory, f"{self.seed}-0-*.jpg")):
            try:
                parts = os.path.basename(chunk).split('-')
                subindex = int(parts[2])
                
                # Сохраняем с размером и subindex перед удалением
                chunks.append({
                    "path": chunk,
                    "size": os.path.getsize(chunk),
                    "subindex": subindex
                })
                
            except (IndexError, ValueError) as e:
                logging.error(f"Неверный формат куска: {chunk} - {e}")
                continue

        # Сортируем куски по subindex и извлекаем пути
        sorted_chunks = sorted(chunks, key=lambda x: x["subindex"])
        chunk_paths = [c["path"] for c in sorted_chunks]
        
        if not chunk_paths:
            logging.error(f"Не найдены куски для seed {self.seed} в директории {directory}")
            return False
        
        return self._reconstruct_file(chunk_paths, output_path) 