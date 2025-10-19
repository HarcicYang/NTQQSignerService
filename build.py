import os
import sys
import subprocess
import shutil


def compile_c_extension():
    print("Compiling C extension...")

    try:
        result = subprocess.run([
            sys.executable, 'setup.py', 'build_ext', '--inplace'
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))

        if result.returncode == 0:
            print("✓ C extension compiled successfully")
            ext_path = None
            for file in os.listdir('.'):
                if file.startswith('sign_extension.') and (file.endswith('.so') or file.endswith('.pyd')):
                    ext_path = file
                    break

            if ext_path:
                print(f"✓ Extension file: {ext_path}")
                return True
            else:
                print("✗ Extension file not found")
                return False
        else:
            print(f"✗ Compilation failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"✗ Compilation error: {e}")
        return False


def compile_symbols_lib():
    print("Compiling symbols library...")

    try:
        result = subprocess.run([
            'gcc', '-std=c99', '-shared', '-fPIC', '-o', 'libsymbols.so', 'symbols.c'
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("✓ Symbols library compiled successfully")
            return True
        else:
            print(f"✗ Symbols compilation failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"✗ Symbols compilation error: {e}")
        return False


def install_python_deps():
    print("Installing Python dependencies...")

    dependencies = [
        'fastapi',
        'uvicorn[standard]',
        'pydantic'
    ]

    for dep in dependencies:
        try:
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', dep
            ], check=True, capture_output=True)
            print(f"✓ Installed {dep}")
        except subprocess.CalledProcessError:
            print(f"✗ Failed to install {dep}")
            return False

    return True


def check_wrapper_node():
    if not os.path.exists('./wrapper.node'):
        print("✗ wrapper.node not found")
        print("Please ensure wrapper.node is available in the current directory")
        return False

    print("✓ wrapper.node found")
    return True


def main():
    print("Building and deploying Sign Service...")
    if not check_wrapper_node():
        print("⚠ Warning: NTQQ files are missing. Please copy them to the current directory before running.")
    if not compile_symbols_lib():
        print("⚠ Continuing without symbols library")
    if not compile_c_extension():
        print("✗ C extension compilation failed")
        sys.exit(1)

    if not install_python_deps():
        print("✗ Python dependency installation failed")
        sys.exit(1)

    print("\n✓ Build completed successfully!")
    print("To start the service: python signer.py")


if __name__ == "__main__":
    main()