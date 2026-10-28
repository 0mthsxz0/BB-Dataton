from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from ligacoes import ResultadoIncerto

ROOT = Path(__file__).resolve().parents[1]
SID = "CA" + "a" * 32


def configurar(monkeypatch):
    monkeypatch.setenv("TWILIO_MODE", "completo")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC" + "b" * 32)
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "c" * 32)
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+5511999999999")


def botao(app, label):
    return next(b for b in app.button if b.label == label)


def test_sem_configuracao_nao_chama_api(monkeypatch):
    for nome in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"):
        monkeypatch.delenv(nome, raising=False)
    with patch("ligacoes.ClienteLigacoes._requisicao") as api:
        app = AppTest.from_file(str(ROOT / "ligacao_interface.py")).run()
        assert not app.exception
        assert "Configure no servidor" in app.info[0].value
        api.assert_not_called()


def test_interface_trial_sem_origem_e_sem_mensagem_personalizada(monkeypatch):
    configurar(monkeypatch)
    monkeypatch.delenv("TWILIO_MODE", raising=False)
    monkeypatch.delenv("TWILIO_FROM_NUMBER", raising=False)
    with patch("ligacoes.ClienteLigacoes._requisicao") as api:
        api.return_value = {"sid": SID, "status": "queued", "duration": None}
        app = AppTest.from_file(str(ROOT / "ligacao_interface.py")).run()
        assert not app.exception
        assert not app.text_area
        assert not app.number_input
        api.assert_not_called()
        app.text_input[0].set_value("+5511888888888")
        app.checkbox[0].check()
        botao(app, "Ligar agora").click().run()
        assert not app.exception
        assert api.call_count == 1
        assert set(api.call_args.kwargs["dados"]) == {"To", "Url"}


def test_fluxo_envio_atualizacao_e_encerramento(monkeypatch):
    configurar(monkeypatch)
    with patch("ligacoes.ClienteLigacoes._requisicao") as api:
        api.return_value = {"sid": SID, "status": "queued", "duration": None}
        app = AppTest.from_file(str(ROOT / "ligacao_interface.py")).run()
        assert not app.exception
        api.assert_not_called()
        app.text_input[0].set_value("+5511888888888")
        botao(app, "Ligar agora").click().run()
        assert app.error
        api.assert_not_called()
        app.checkbox[0].check()
        botao(app, "Ligar agora").click().run()
        assert not app.exception
        assert api.call_count == 1
        assert botao(app, "Ligar agora").disabled
        app.run()
        assert api.call_count == 1
        api.return_value = {"sid": SID, "status": "in-progress", "duration": None}
        botao(app, "Atualizar status").click().run()
        assert api.call_args.args == ("/" + SID,)
        api.return_value = {"sid": SID, "status": "completed", "duration": "10"}
        botao(app, "Encerrar chamada").click().run()
        assert api.call_args.args == ("/" + SID, {"Status": "completed"})
        assert not app.exception
        assert not botao(app, "Ligar agora").disabled
        assert botao(app, "Encerrar chamada").disabled


def test_timeout_bloqueia_novo_envio(monkeypatch):
    configurar(monkeypatch)
    with patch("ligacoes.ClienteLigacoes._requisicao", side_effect=ResultadoIncerto("Timeout")) as api:
        app = AppTest.from_file(str(ROOT / "ligacao_interface.py")).run()
        app.text_input[0].set_value("+5511888888888")
        app.checkbox[0].check()
        botao(app, "Ligar agora").click().run()
        assert not app.exception
        assert botao(app, "Ligar agora").disabled
        assert app.warning
        app.run()
        assert api.call_count == 1
        botao(app, "Já conferi os logs; liberar novo envio").click().run()
        assert not botao(app, "Ligar agora").disabled
        assert api.call_count == 1


def test_ligacoes_no_app_principal_sem_csv(monkeypatch):
    configurar(monkeypatch)
    with patch("ligacoes.ClienteLigacoes._requisicao") as api:
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        app.sidebar.radio[0].set_value("Ligações").run()
        assert not app.exception
        assert app.title[0].value == "Ligações por telefone"
        assert botao(app, "Ligar agora")
        api.assert_not_called()
