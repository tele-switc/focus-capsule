# Focus Capsule

Focus Capsule 是一个使用 Python 与 PyQt6 构建的桌面专注工具。项目提供 Windows
one-dir 应用、Windows 安装器，以及原生 macOS `.app`/`.dmg` 的可复现构建配置。

## 本地运行

建议使用独立虚拟环境：

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m focus_capsule
```

macOS 使用对应的 `python3` 与 `.venv/bin/python`。`requirements.txt` 使用环境标记，
只会在 Windows 安装 `pywin32`，在 macOS 安装 Cocoa 的 PyObjC bridge。

## 版本

发布版本的唯一来源是 `packaging/version.txt`。修改版本后需要同步生成 Windows
版本资源：

```powershell
python packaging/generate_version_info.py
python packaging/generate_version_info.py --check
```

CI 会执行 `--check`，避免安装器版本、应用版本和 Git 标签发生漂移。发布标签建议使用
`v1.0.0` 格式，并与文件中的 `1.0.0` 保持一致。

## Windows 构建

Windows 使用 PyInstaller one-dir 模式，再由 Inno Setup 生成无需管理员权限的
per-user 安装器。首次构建前安装 Inno Setup 6：

```powershell
winget install --id JRSoftware.InnoSetup -e
.\packaging\build_windows.ps1
```

脚本会创建 `.venv-build`、安装受控版本的构建依赖、从 SVG 生成多尺寸 ICO、生成
PE 版本资源并输出：

- `dist/Focus Capsule/`：便携 one-dir 应用；
- `dist/installer/Focus-Capsule-<version>-Windows-x64-Setup.exe`；
- 与安装器同名的 `.sha256` 校验文件。

只构建便携应用可使用 `-SkipInstaller`。在已有 Python 环境中可使用：

```powershell
.\packaging\build_windows.ps1 -Python python -SkipDependencyInstall
```

若设置 `WINDOWS_SIGN_PFX` 和 `WINDOWS_SIGN_PASSWORD`，脚本会使用 Windows SDK 的
`signtool.exe` 对应用和安装器签名。发布流水线可额外传入
`-RequireSigning`，让缺少证书时立即失败。

## macOS 构建

PyInstaller 不能从 Windows 交叉构建 macOS 应用，必须在 macOS 或 macOS CI runner
上运行：

```bash
bash packaging/build_macos.sh
```

脚本使用 PyQt6 原生 SVG 渲染与系统 `iconutil` 生成 ICNS，构建 `.app`，再使用
`hdiutil` 生成带 Applications 快捷方式的 DMG。产物位于
`dist/dmg/Focus-Capsule-<version>-macOS-<architecture>.dmg`。

可选环境变量：

- `MACOS_CODESIGN_IDENTITY`：Developer ID Application 证书名称；
- `PYINSTALLER_ARCH`：构建架构，必须受当前 Python 和所有二进制 wheel 支持；
- `APPLE_NOTARY_KEYCHAIN_PROFILE`：已保存的 notarytool profile；
- 或同时设置 `APPLE_ID`、`APPLE_TEAM_ID`、`APPLE_APP_PASSWORD` 完成公证。

没有签名和公证凭证时仍可生成开发测试包，但 Gatekeeper 会向最终用户显示警告。
Intel 与 Apple Silicon 的生产包应在各自架构的 runner 上分别构建；只有 Python、
PyQt6、psutil 和 PyObjC 全部提供 universal2 二进制时才应启用 universal2。

## CI

`.github/workflows/build-desktop.yml` 在发布标签、手动触发和相关 Pull Request 上运行：

- `windows-latest` 构建 Inno Setup 安装器；
- `macos-latest` 构建当前 runner 架构的 DMG；
- 两个平台都上传安装包和 SHA-256 文件；
- 有签名 secrets 时执行签名，macOS 凭证完整时还会执行 notarization 与 stapling。

CI secrets：

- Windows：`WINDOWS_CERTIFICATE_BASE64`、`WINDOWS_SIGN_PASSWORD`；
- macOS：`MACOS_CERTIFICATE_BASE64`、`MACOS_CERTIFICATE_PASSWORD`、
  `MACOS_CODESIGN_IDENTITY`；
- 公证：`APPLE_ID`、`APPLE_TEAM_ID`、`APPLE_APP_PASSWORD`。

证书文件、生成的 `.ico/.icns`、构建目录和安装包均已加入 `.gitignore`。

## PyQt6 许可

PyPI 提供的 PyQt6 是 GPLv3 版本。Riverbank 将 PyQt 以 GPLv3 或商业许可证双重授权，
且 PyQt 本身不提供 LGPL 版本。如果发行许可证不兼容 GPL，需要在发布前购买适用的
PyQt 商业许可证，或评估迁移到其他具有合适许可条件的 Qt Python bindings。

请参阅 [Riverbank 官方许可说明](https://www.riverbankcomputing.com/software/pyqt/intro/)；
本节仅用于提示发布决策，不构成法律意见。
