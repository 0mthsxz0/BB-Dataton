from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_fluxo_interface_comparacao_e_simulacao(pasta_csv,monkeypatch):
    monkeypatch.setenv('BB_DATATHON_DADOS',str(pasta_csv))
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
    assert not app.exception
    assert app.metric[0].value=='1'
    app.sidebar.radio[0].set_value('Analisar estabelecimento').run()
    assert not app.exception
    assert any(m.label=='Plano sugerido' for m in app.metric)
    app.sidebar.radio[0].set_value('Comparar').run()
    assert not app.exception
    app.selectbox[-1].set_value('IMO_FILIAL').run()
    assert not app.exception
    app.sidebar.radio[0].set_value('Simular cenários').run()
    assert not app.exception
    app.slider[0].set_value(2.).run()
    assert not app.exception
    app.sidebar.radio[0].set_value('Exportar').run()
    app.button[0].click().run()
    assert not app.exception
    assert any('2 estabelecimentos' in s.value for s in app.success)
