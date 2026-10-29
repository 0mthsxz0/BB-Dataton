import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pandas as pd
import pytest

from scripts.preencher_templates_api import consultar, preencher
from templates_api import ENDPOINT, ServicoTemplates, criar_servidor

TOKEN = 'token-sintetico-apenas-para-testes-123456'


@pytest.fixture
def api(pasta_csv):
    template = pasta_csv / 'template_resultado_times.csv'
    colunas = pd.read_csv(template).columns
    unidades = pd.read_csv(pasta_csv / 'enderecos_estabelecimentos.csv')[['empresa_id', 'imovel_id']]
    unidades.reindex(columns=colunas, fill_value='').to_csv(template, index=False)
    service = ServicoTemplates(pasta_csv, data_analise='2026-10-29')
    server = criar_servidor(service, TOKEN, 0)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    yield service, f'http://127.0.0.1:{server.server_port}'
    server.shutdown()
    server.server_close()
    worker.join(timeout=5)


def test_http_por_unidade_equivale_ao_lote_sem_perder_filiais(api, pasta_csv, tmp_path):
    service, url = api
    out = tmp_path / 'entrega'
    manifest = preencher(url, TOKEN, pasta_csv / 'template_resultado_times.csv', out, service)
    assert manifest['chamadas_recomendacao'] == 2
    assert manifest['comparacao_lote']['valores_identicos']
    assert manifest['comparacao_lote']['csvs_identicos_byte_a_byte']
    assert all(x['status_http'] == 200 for x in json.loads((out / 'chamadas_api.json').read_text(encoding='utf-8')))
    assert service.base.registro('EMP_TESTE', 'IMO_TESTE')['quantidade_unidades'] == 2


@pytest.mark.parametrize('payload,status', [
    ({'empresa_id': 'EMP_TESTE'}, 422),
    ({'empresa_id': 'EMP_TESTE', 'imovel_id': 'INEXISTENTE'}, 404),
    ({'empresa_id': 'EMP_TESTE', 'imovel_id': 'IMO_TESTE', 'answers': {}}, 422),
    ({'empresa_id': [], 'imovel_id': 'IMO_TESTE'}, 422),
])
def test_http_rejeita_entrada_invalida(api, payload, status):
    _, url = api
    with pytest.raises(HTTPError) as exc:
        consultar(url + ENDPOINT, TOKEN, payload)
    assert exc.value.code == status


def test_nao_expoe_base_sem_token_e_rejeita_browser(api):
    _, url = api
    with pytest.raises(HTTPError) as exc:
        consultar(url + '/api/templates/contrato', 'incorreto')
    assert exc.value.code == 401
    req = Request(url + '/api/templates/contrato', headers={'Authorization': 'Bearer ' + TOKEN, 'Origin': 'http://outro-site'})
    with pytest.raises(HTTPError) as exc:
        urlopen(req)
    assert exc.value.code == 403


def test_bloqueio_retorna_resultado_sem_coberturas(api):
    service, url = api
    service.base.estabelecimentos.loc[service.base.estabelecimentos.imovel_id.eq('IMO_TESTE'), 'situacao_imovel_cadastral'] = 'EM_OBRA'
    response = consultar(url + ENDPOINT, TOKEN, {'empresa_id': 'EMP_TESTE', 'imovel_id': 'IMO_TESTE'})
    assert response['resultado']['elegivel'] == 'NAO'
    assert response['resultado']['plano_recomendado'] == ''
    assert response['coberturas'] == []


def test_falha_na_segunda_chamada_nao_publica_csv_parcial(api, pasta_csv, tmp_path, monkeypatch):
    service, url = api
    recomendar = service.recomendar
    def falhar(payload):
        if payload['imovel_id'] == 'IMO_FILIAL':
            raise RuntimeError('Falha sintética')
        return recomendar(payload)
    monkeypatch.setattr(service, 'recomendar', falhar)
    with pytest.raises(HTTPError):
        preencher(url, TOKEN, pasta_csv / 'template_resultado_times.csv', tmp_path / 'entrega')
    assert not (tmp_path / 'entrega').exists()


def test_pasta_existente_nao_e_sobrescrita(api, pasta_csv, tmp_path):
    _, url = api
    with pytest.raises(ValueError, match='já existe'):
        preencher(url, TOKEN, pasta_csv / 'template_resultado_times.csv', tmp_path)
