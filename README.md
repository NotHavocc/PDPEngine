# PDPEngine <img src="https://cdn.discordapp.com/attachments/1515312988989689908/1550888660537315428/logo.png?ex=6aaff91e&is=6aaea79e&hm=247abec053d6fc02b1f86f002cf84230ecf8975cd9c33210b66bbf23d1d9fb70&" width="100" align="left">
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/NotHavocc/PDPEngine/total)
![GitHub Release](https://img.shields.io/github/v/release/NotHavocc/PDPEngine)
![Static Badge](https://img.shields.io/badge/open_source-with_%3C3-blue)\
A cross-platform desktop pet engine derived from [PinkDesktopPet](https://gtihub.com/NotHavocc/PinkDesktopPet) \
\
[Download](https://github.com/NotHavocc/PDPEngine#download)
[Documentation](https://github.com/NotHavocc/PDPEngine/blob/main/docs/README.md)
> [!NOTE]
> if youre using Windows: the settings are at the right side of the taskbar, where the wifi icon is and etc. by default its hidden behind the arrow thing, click on it and youll see the icon


## download

> [!WARNING]  
> windows defender may pop up and say that this is a virus, it indeed isnt. the code is fully open source so if youre skeptical, you can check it yourself too.

[Download for Windows (.exe)](https://github.com/NotHavocc/PDPEngine/releases/latest/download/PDPEngine.exe)\
[Universal Script (any platform) (.py)](https://github.com/NotHavocc/PinkDesktopPet/archive/refs/heads/main.zip)\
(macOS onefile executable will release soon, there are some issues currently with PyQT on macOS)\
\
to use the universal script, you need python downloaded on your machine

## dependencies
run this command in your OSes terminal\
\
**windows/any os with pip (with no --break-system-packages)**
```
pip install PyQt6
```
\
**debian/debian based linux, audio dependencies needed too**
```
sudo apt install python3-pip gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly
pip3 install PyQt6
```
(same would go for other distros, just use your respective package manager)

### for developers

these are the commands used for compiling the .py project into .exe (or the respective platform's executable)\
\
**windows**
```
pyinstaller --noconfirm --onefile --windowed --name "PDPEngine" --add-data "assets;assets" --hidden-import PyQt6.QtMultimedia main.pyw
```
\
**macOS/linux**
```
pyinstaller --noconfirm --onefile --windowed --name "PDPEngine" --add-data "assets:assets" --hidden-import PyQt6.QtMultimedia main.pyw
```



