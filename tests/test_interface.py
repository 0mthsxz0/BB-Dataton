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


def test_consulta_cep_interface(pasta_csv, monkeypatch):
    monkeypatch.setenv('BB_DATATHON_DADOS', str(pasta_csv))
    from unittest.mock import Mock
    monkeypatch.setattr('localizacao.requests.get', Mock(return_value=Mock(json=lambda: {
        'cep': '01001-000', 'ibge': '3550308', 'localidade': 'São Paulo',
        'uf': 'SP', 'bairro': 'Sé', 'logradouro': 'Praça da Sé'})))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'), default_timeout=60).run()
    app.sidebar.radio[0].set_value('Consultar por CEP').run()
    next(x for x in app.text_input if x.label == 'CEP').set_value('01001-000')
    next(x for x in app.button if x.label == 'Consultar CEP').click().run()
    assert not app.exception
    assert any('São Paulo/SP' in x.value for x in app.success)
    assert any('município inteiro' in x.value for x in app.info)
    app.checkbox[0].check().run()
    assert not app.exception
    assert any(x.label == 'Plano sugerido' for x in app.metric)
    next(x for x in app.text_input if x.label == 'CEP').set_value('123')
    next(x for x in app.button if x.label == 'Consultar CEP').click().run()
    assert any('oito dígitos' in x.value for x in app.error)
    assert not any('São Paulo/SP' in x.value for x in app.success)
