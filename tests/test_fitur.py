"""Fitur klasterisasi (Langkah 5 putaran 2): 9 variabel aksesibilitas, tanpa kelas bahaya."""
from backend import thesis as T
from backend.engine import Cfg


def test_sembilan_fitur_tanpa_kelas_bahaya():
    cols = T.feature_columns(Cfg())
    assert len(cols) == 9
    assert T.SKENARIO not in cols
    assert T.SKENARIO in T.PROFILE_COLS          # tetap deskriptif di profil klaster
