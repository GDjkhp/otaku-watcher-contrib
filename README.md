<div align="center">

  # otaku-watcher-contrib
  <img src="https://gdjkhp.github.io/img/kagura-merge-avatar.gif" width=64>

  <sub>A mov-cli plugin for watching anime and more!</sub>

  [![Pypi Version](https://img.shields.io/pypi/v/otaku-watcher-contrib?style=flat)](https://pypi.org/project/otaku-watcher-contrib)

  <img src="https://gdjkhp.github.io/img/gintama.png">
</div>

## ⛑️ Support
| Scraper | Status | Films | TV | Mobile support |
| ------- | ------ | --- | --- | ---------------------- |
| [`tokyo`](https://www.tokyoinsider.com) | 🔵 Experimental | ✅ | ✅ | ✅ |
| [`hianime`](https://hianime.to) | 🔵 Experimental | ✅ | ✅  | ❓ |
| [`animepahe`](https://animepahe.ru) | 🔵 Experimental | ✅ | ✅  | ❓ |
| [`kisskh`](https://kisskh.id) | 🔵 Experimental | ✅ | ✅  | ❓ |

## Installation
Here's how to install and add the plugin to mov-cli.

1. Install the pip package.
```sh
pip install otaku-watcher-contrib
```
2. Then add the plugin to your mov-cli config.
```sh
mov-cli -e
```
```toml
[mov-cli.plugins]
anime = "otaku-watcher-contrib"
```
## Usage
```sh
mov-cli lycoris recoil
```