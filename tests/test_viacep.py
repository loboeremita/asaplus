import json
import urllib.error
from unittest.mock import MagicMock, patch
import pytest
from beneficiaries.services.viacep import (
    AddressData,
    CEPNotFoundError,
    InvalidCEPError,
    ViaCEPConnectionError,
    ViaCEPService,
)


class TestViaCEPService:
    def test_clean_cep_valid(self):
        assert ViaCEPService.clean_cep("40000-000") == "40000000"
        assert ViaCEPService.clean_cep("40000000") == "40000000"
        assert ViaCEPService.clean_cep(" 40.000-000 ") == "40000000"

    def test_clean_cep_invalid_length(self):
        with pytest.raises(InvalidCEPError, match="deve conter exatamente 8 dígitos"):
            ViaCEPService.clean_cep("1234")

        with pytest.raises(InvalidCEPError):
            ViaCEPService.clean_cep("1234567890")

        with pytest.raises(InvalidCEPError):
            ViaCEPService.clean_cep("")

    @patch("urllib.request.urlopen")
    def test_fetch_address_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "cep": "40020-000",
            "logradouro": "Avenida Sete de Setembro",
            "complemento": "Lado Par",
            "bairro": "Centro",
            "localidade": "Salvador",
            "uf": "BA",
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        address = ViaCEPService.fetch_address("40020-000")

        assert isinstance(address, AddressData)
        assert address.cep == "40020-000"
        assert address.street == "Avenida Sete de Setembro"
        assert address.neighborhood == "Centro"
        assert address.city == "Salvador"
        assert address.state == "BA"
        assert address.complement == "Lado Par"

    @patch("urllib.request.urlopen")
    def test_fetch_address_cep_not_found(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"erro": True}).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with pytest.raises(CEPNotFoundError, match="não foi localizado"):
            ViaCEPService.fetch_address("99999-999")

    @patch("urllib.request.urlopen")
    def test_fetch_address_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")

        with pytest.raises(ViaCEPConnectionError, match="Erro de conexão"):
            ViaCEPService.fetch_address("40020-000")
