# -*- coding: utf-8 -*-
"""İzin Takip Sistemi — başlatıcı (PyInstaller giriş noktası; geliştirmede: python baslat.py)."""
import os
import sys

if not getattr(sys, 'frozen', False):
    _kok = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, _kok)

from izin_takip.uygulama import main  # noqa: E402

if __name__ == '__main__':
    sys.exit(main())
