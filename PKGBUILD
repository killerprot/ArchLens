pkgname=archlens-git
pkgver=0.1.0.r1.g0000000
pkgrel=1
pkgdesc='Explain Arch Linux package dependencies and removal impact'
arch=('any')
url='https://github.com/killerprot/ArchLens'
depends=('python' 'python-pyside6')
makedepends=('git' 'python-build' 'python-installer')
source=('git+https://github.com/killerprot/ArchLens.git')
sha256sums=('SKIP')

pkgver() {
  cd ArchLens
  printf '0.1.0.r%s.g%s' "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)"
}

build() {
  cd ArchLens
  python -m build --wheel --no-isolation
}

package() {
  cd ArchLens
  python -m installer --destdir="$pkgdir" dist/*.whl
  install -Dm644 data/archlens.desktop "$pkgdir/usr/share/applications/archlens.desktop"
  install -Dm644 data/archlens.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/archlens.svg"
}
