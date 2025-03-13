import os
import subprocess
import sys

def obfuscate_and_compile():
    """
    Обфусцирует и компилирует скрипт в EXE файл
    """
    # Путь к основному файлу скрипта
    main_file = os.path.join(os.path.dirname(__file__), "__main__.py")
    
    # Команда для обфускации с помощью PyArmor
    obfuscate_cmd = [
        "pyarmor", "obfuscate",
        "--restrict", "0",
        "--output", "dist",
        main_file
    ]
    
    # Команда для компиляции в EXE с помощью PyInstaller
    compile_cmd = [
        "pyinstaller",
        "--onefile",
        "--name", "crypto_tool",
        "--distpath", "dist",
        "--workpath", "build",
        "--specpath", "build",
        os.path.join("dist", "__main__.py")
    ]
    
    try:
        # Выполняем обфускацию
        print("Обфускация кода...")
        subprocess.run(obfuscate_cmd, check=True)
        
        # Выполняем компиляцию
        print("Компиляция в EXE...")
        subprocess.run(compile_cmd, check=True)
        
        print("Компиляция успешно завершена. EXE файл находится в папке dist/")
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды: {e}")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    obfuscate_and_compile()
