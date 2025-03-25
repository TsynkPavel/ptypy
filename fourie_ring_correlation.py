import numpy as np
import cv2
import matplotlib.pyplot as plt
from scipy.fft import fft2, fftshift
import argparse

def load_and_preprocess(image_path, size=(3000, 3000)):
    """Загружает изображение, переводит в оттенки серого и приводит к нужному размеру"""
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)  # Читаем в grayscale
    # img = cv2.resize(img, size)  # Приводим к 3000x3000
    img = img - np.mean(img)  # Центрируем, чтобы избежать DC-компоненты
    return img

def compute_frc(image1, image2):
    """Вычисляет FRC между двумя изображениями размером 3000x3000"""
    # 2D Фурье-преобразование
    F1 = fftshift(fft2(image1))
    F2 = fftshift(fft2(image2))

    # Вычисляем FRC
    cross_power_spectrum = np.real(F1 * np.conj(F2))
    power_spectrum_1 = np.abs(F1) ** 2
    power_spectrum_2 = np.abs(F2) ** 2

    # Координаты центра
    h, w = image1.shape
    y, x = np.indices((h, w))
    center = (h // 2, w // 2)
    r = np.sqrt((x - center[1]) ** 2 + (y - center[0]) ** 2).astype(np.int32)

    # Вычисляем FRC по кольцевым областям
    frc = np.bincount(r.ravel(), weights=cross_power_spectrum.ravel()) / (
        np.sqrt(
            np.bincount(r.ravel(), weights=power_spectrum_1.ravel()) *
            np.bincount(r.ravel(), weights=power_spectrum_2.ravel())
        )
    )

    # Нормализуем пространственную частоту
    freq = np.arange(len(frc)) / (h / 2)

    return freq, frc

def plot_2d_fft(image, output_name, title="2D Fourier Transform"):
    """Визуализирует 2D Фурье-преобразование изображения"""
    magnitude_spectrum = np.log(1 + np.abs(fftshift(fft2(image))))  # Логарифмическая шкала

    plt.figure(figsize=(8, 5))
    plt.imshow(magnitude_spectrum, cmap='inferno')
    plt.title(title)
    plt.axis("off")
    # plt.show()
    plt.savefig(
        f"results/FRC/{output_name}",
        dpi=400,
        bbox_inches="tight"
    )

def compute_pixel_size(freq, frc, image_size, physical_size=None):
    """Вычисляет реальный размер пикселя на основе FRC"""
    threshold = 1/7  # Граница отсечения
    cutoff_idx = np.where(frc < threshold)[0][0]  # Индекс первого пересечения
    cutoff_freq = freq[cutoff_idx]  # Найденная частота отсечения

    pixel_size = 1 / (cutoff_freq * image_size) * 1000  # Размер пикселя в относительных единицах

    if physical_size:
        pixel_size *= physical_size  # Перевод в реальные единицы

    return pixel_size, cutoff_freq


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file-1", dest="file_1", type=str)
    parser.add_argument("--file-2", dest="file_2", type=str)

    args = parser.parse_args()

    # Загружаем изображения звезды Симонса 3000x3000
    image1 = load_and_preprocess(args.file_1)
    image2 = load_and_preprocess(args.file_2)
    
    plot_2d_fft(image1, output_name="A_Reference_2D.png", title="2D FFT of Image A")
    plot_2d_fft(image2, output_name="B_Reference_2D.png", title="2D FFT of Image B")

    # Вычисляем FRC
    # freq, frc = compute_frc(image1, image2)

    # # Визуализация FRC
    # plt.figure(figsize=(8, 5))
    # plt.plot(freq, frc, label="FRC Curve", linewidth=2)
    # plt.axhline(y=1/7, color="r", linestyle="--", label="1/7 threshold")
    # plt.xlabel("Spatial Frequency")
    # plt.ylabel("FRC")
    # plt.legend()
    # plt.title("Fourier Ring Correlation (FRC) for 3000x3000 Images")
    # plt.grid()
    # # plt.show()
    # plt.savefig(
    #     "results/FRC/FRC.png",
    #     dpi=800,
    #     bbox_inches="tight"
    # )
    
    # # Пример вызова
    # image_size = 3000  # Размер изображения (в пикселях)
    # physical_size = 12  # Физический размер изображения (например, в микрометрах)

    # pixel_size, cutoff_freq = compute_pixel_size(freq, frc, image_size, physical_size)

    # print(f"Частота отсечения: {cutoff_freq:.3f}")
    # print(f"Реальный размер пикселя: {pixel_size:.3f} нм")


