from ptypy import io
import numpy as np
import matplotlib.pyplot as plt

import os

import argparse

# [x] Рисовать картинку с лучем.
# content["pars"]["scans"]["scan00"]["data"]["sample"]["model"] с `np.angle(data)` и `data.imag`
# [x] Проверить что она содержит информацию, как-то увеличить.
# Изображение 3351 х 3351. Центр [1676][1676]. Если просто достать элемент, это ничего не дает.
# Можно попробовать выделить 100 пикселей из центра и из них построить картинку.
# Нужно выделить область 1625 -> 1675 -> 1726
# [x] Добавить функцию обрезки изображения
# [ ] Выставить cmap как в ptypy
# [ ] Поиграться с фурье, чтобы не было точек артифактов


def get_crop_ndarray(data, reference: np.ndarray, size: int) -> np.ndarray:
    # Если изображение имеет четное количетсво элементов по всем осям,
    # его центр будет смещен на 1 пиксель
    result: np.ndarray = np.ndarray(shape=(size, size))

    if reference.ndim != 2:
        raise NotImplementedError(
            f"Не поддерживается обработка {reference.ndim}D объектов. Только 2D"
        )

    reference_size_is_even = reference[0].size % 2 == 0
    center = (
        int(reference[0].size / 2)
        if reference_size_is_even
        else int((reference[0].size / 2) + 1)
    )
    start = int(center - (size / 2))
    finish = int(center + (size / 2))

    assert (finish - start) == size

    for y, yy in enumerate(range(start, finish)):
        for x, xx in enumerate(range(start, finish)):
            result[y][x] = data[xx][yy]

    return result


def main(args):
    DPI = 800
    CMAP = "CMRmap"  # "hsv"  # twilight
    BBOX_INCHES = "tight"
    subfolder = os.path.join(args.subfolder, CMAP)
    os.makedirs(name=subfolder, exist_ok=True)

    data = io.h5read(args.ptyr_file)
    content = data["content"]

    data = content["probe"]["Sscan00G00"]["data"]
    data = np.squeeze(data)

    if True:
        if args.crop is None:
            data = content["obj"]["Sscan00G00"]["data"]
            data = np.squeeze(data)
            plt.imshow(np.abs(data), cmap=CMAP)
            plt.title("A")
            plt.colorbar()
            plt.savefig(
                os.path.join(subfolder, "A.png"),
                dpi=DPI,
                bbox_inches=BBOX_INCHES,
            )
            plt.show()

        if args.crop is None:
            plt.imshow(data.imag, cmap=CMAP)
            # plt.axis("off")
            plt.title("P")
            # plt.colorbar()
            plt.savefig(
                os.path.join(subfolder, "P.png"),
                dpi=DPI,
                bbox_inches=BBOX_INCHES,
            )

        if args.crop is None:
            data = content["pars"]["scans"]["scan00"]["data"]["sample"]["model"]
            data = np.squeeze(data)
            plt.imshow(np.abs(data), cmap=CMAP)
            plt.title("Reference")
            # plt.colorbar()
            plt.savefig(
                os.path.join(subfolder, "Reference.png"),
                dpi=DPI,
                bbox_inches=BBOX_INCHES,
            )

        data = content["probe"]["Sscan00G00"]["data"]
        data = np.squeeze(data)
        fig_outname = "C"

        if args.log:
            data = np.log(data)
            fig_outname += "_log"
        if args.crop is not None:
            data = get_crop_ndarray(data, reference=data, size=args.crop)
            fig_outname += f"_crop_{args.crop}"
            # plt.colorbar()

        fig_outname += ".png"

        plt.imshow(np.abs(data), cmap=CMAP)
        plt.title("C")
        plt.savefig(
            os.path.join(subfolder, fig_outname),
            dpi=DPI,
            bbox_inches=BBOX_INCHES,
        )
        ###########
        # plt.show()


# data = content["probe"]["Sscan00G00"]["data"]
# logging.info(f"BOOM_3_shape: {content["probe"]["Sscan00G00"]["shape"]}")
# logging.info(f"BOOM_3_data: {da ta}")

# data = np.squeeze(data)

# plt.imshow(np.abs(data), cmap="viridis")
# plt.title("Amplitude (Magnitude) of Complex Data")
# # plt.savefig("high_res_image.png", dpi=DPI, bbox_inches=BBOX_INCHES)
# # plt.colorbar()
# plt.show()

# plt.imshow(np.angle(data), cmap=CMAP)
# # plt.imshow(new_data, cmap=CMAP)
# plt.title("Phase of Complex Data")
# # plt.colorbar()
# plt.show()

# plt.imshow(data.real, cmap="viridis")
# plt.title("Real Part of Complex Data")
# # plt.colorbar()
# plt.show()

# plt.imshow(data.imag, cmap="viridis")
# plt.title("Imaginary Part of Complex Data")
# # plt.colorbar()
# # plt.savefig("high_res_image.png", dpi=DPI, bbox_inches=BBOX_INCHES)
# plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--subfolder", dest="subfolder", type=str)
    parser.add_argument("--ptyr-file", dest="ptyr_file", type=str)
    parser.add_argument("--crop", dest="crop", default=None, type=int)
    parser.add_argument("--log", dest="log", default=False, action="store_true")
    args = parser.parse_args()

    main(args)
