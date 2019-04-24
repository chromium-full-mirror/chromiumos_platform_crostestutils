# BASE PREP:
sudo apt-get update
sudo apt-get dist-upgrade

# DEPENDENCIES:
sudo apt-get update -qq && sudo apt-get -y install \
  alsa-utils \
  autoconf \
  automake \
  build-essential \
  cmake \
  dtrx \
  git-core \
  libasound2-dev \
  libasound2-plugins:i386 \
  libass-dev \
  libfdk-aac-dev \
  libfreetype6-dev \
  libtool \
  libvorbis-dev \
  libx264-dev \
  nasm \
  pkg-config \
  texinfo \
  v4l-utils \
  wget \
  yasm \
  zlib1g-dev

mkdir -p ~/ffmpeg_sources ~/bin


# Build and install FFMPEG
cd ~/ffmpeg_sources && \
wget -O ffmpeg-snapshot.tar.bz2 https://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2 && \
tar xjvf ffmpeg-snapshot.tar.bz2 && \
cd ffmpeg && \
PATH="$HOME/bin:$PATH" PKG_CONFIG_PATH="$HOME/ffmpeg_build/lib/pkgconfig" ./configure \
  --prefix="$HOME/ffmpeg_build" \
  --pkg-config-flags="--static" \
  --extra-cflags="-I$HOME/ffmpeg_build/include" \
  --extra-ldflags="-L$HOME/ffmpeg_build/lib" \
  --extra-libs="-lpthread -lm" \
  --bindir="$HOME/bin" \
  --enable-gpl \
  --enable-libass \
  --enable-libfdk-aac \
  --enable-libfreetype \
  --enable-libx264 \
  --enable-nonfree && \
PATH="$HOME/bin:$PATH" make -j4 && \
make install && \
hash -r

cd ~
