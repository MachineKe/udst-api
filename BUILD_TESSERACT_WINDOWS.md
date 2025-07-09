# Building Tesseract 5.5.1 from Source on Windows

These instructions will help you build `tesseract.exe` from the source you have at:
`C:\Users\marka\Downloads\Compressed\tesseract-5.5.1\tesseract-5.5.1`

## Prerequisites

1. **Visual Studio 2019 or 2022** (Community Edition is fine)
   - During installation, select the "Desktop development with C++" workload.
2. **CMake** (https://cmake.org/download/)
3. **Git** (https://git-scm.com/download/win)
4. **Leptonica** (Tesseract's image processing dependency)
5. **vcpkg** (recommended for managing dependencies)

## Steps

### 1. Install vcpkg (Dependency Manager)

Open a terminal (cmd or PowerShell):

```sh
git clone https://github.com/microsoft/vcpkg.git
cd vcpkg
bootstrap-vcpkg.bat
```

### 2. Install Leptonica and Other Dependencies

```sh
vcpkg install leptonica:x64-windows
vcpkg install zlib:x64-windows
vcpkg install libpng:x64-windows
vcpkg install jpeg-turbo:x64-windows
vcpkg install libtiff:x64-windows
```

### 3. Configure the Build with CMake

Open "x64 Native Tools Command Prompt for VS 2019/2022" (from Start Menu).

Navigate to your Tesseract source directory:

```sh
cd C:\Users\marka\Downloads\Compressed\tesseract-5.5.1\tesseract-5.5.1
mkdir build
cd build
```

Configure with CMake, pointing to vcpkg:

```sh
cmake .. -DCMAKE_TOOLCHAIN_FILE=[path_to_vcpkg]/scripts/buildsystems/vcpkg.cmake -DCMAKE_BUILD_TYPE=Release
```
Replace `[path_to_vcpkg]` with the path where you cloned vcpkg.

### 4. Build Tesseract

Still in the build directory, run:

```sh
cmake --build . --config Release
```

This will generate `tesseract.exe` in the `Release` subdirectory.

### 5. Add Tesseract to PATH or Configure pytesseract

- Add the directory containing `tesseract.exe` to your system PATH, **or**
- In your Python code, set:
  ```python
  import pytesseract
  pytesseract.pytesseract.tesseract_cmd = r"C:\Users\marka\Downloads\Compressed\tesseract-5.5.1\tesseract-5.5.1\build\Release\tesseract.exe"
  ```

### 6. Download Language Data Files

Download language `.traineddata` files from:
https://github.com/tesseract-ocr/tessdata

Place them in a `tessdata` folder next to `tesseract.exe` or specify the path with the `--tessdata-dir` argument.

---

**If you encounter errors, please copy the error message and let me know.**
