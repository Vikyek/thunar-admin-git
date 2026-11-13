# Maintainer: Local System Administrator
pkgname=thunar-admin-git
pkgver=4.21.6.256.g92d623b57
pkgrel=1
pkgdesc="Thunar File Manager patched for UCA custom actions on admin:// URIs"
arch=('x86_64')
url="https://gitlab.xfce.org/xfce/thunar"
license=('GPL-2.0-or-later' 'LGPL-2.1-or-later')
depends=(
  'exo' 'libxfce4ui' 'libpng' 'desktop-file-utils' 'libgudev'
  'libnotify' 'pcre2' 'hicolor-icon-theme' 'libglib-2.0.so'
)
makedepends=('git' 'meson' 'ninja' 'gobject-introspection' 'xfce4-dev-tools' 'python')
provides=('thunar')
conflicts=('thunar')
source=('git+https://gitlab.xfce.org/xfce/thunar.git#branch=xfce-4.20'
        'patch_uca.py')
sha256sums=('SKIP' 'SKIP')

pkgver() {
  cd "$srcdir/thunar"
  git describe --long --tags 2>/dev/null | sed 's/^thunar-//;s/-/./g' || printf "r%s.%s" "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)"
}

prepare() {
  cd "$srcdir"
  python3 "$srcdir/patch_uca.py"
}

build() {
  rm -rf build
  arch-meson thunar build -Dthunar-tpa=disabled
  meson compile -C build
}

package() {
  meson install -C build --destdir "$pkgdir"
}
