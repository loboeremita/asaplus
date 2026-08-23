from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from common.exceptions import ApplicationError, NotFoundError, ValidationError


class InvalidCEPError(ValidationError):
    """Raised when the provided CEP format is invalid."""


class CEPNotFoundError(NotFoundError):
    """Raised when the CEP does not exist in ViaCEP database."""


class ViaCEPConnectionError(ApplicationError):
    """Raised when connection to ViaCEP fails or times out."""


@dataclass(frozen=True)
class AddressData:
    cep: str
    street: str
    neighborhood: str
    city: str
    state: str
    complement: str = ""


class ViaCEPService:
    """
    Service responsible for validating CEPs and retrieving address details from ViaCEP API.
    """

    BASE_URL = "https://viacep.com.br/ws/{cep}/json/"

    @classmethod
    def clean_cep(cls, cep: str) -> str:
        """
        Sanitizes and validates CEP format (must be 8 numeric digits).
        """
        if not cep or not isinstance(cep, str):
            raise InvalidCEPError("CEP inválido. O valor não pode ser vazio.")

        cleaned = re.sub(r"\D", "", cep)
        if len(cleaned) != 8:
            raise InvalidCEPError(f"CEP '{cep}' inválido. Um CEP válido deve conter exatamente 8 dígitos numéricos.")

        return cleaned

    @classmethod
    def fetch_address(cls, cep: str, timeout: int = 5) -> AddressData:
        """
        Fetches address data from ViaCEP API for a given CEP.
        """
        cleaned_cep = cls.clean_cep(cep)
        url = cls.BASE_URL.format(cep=cleaned_cep)

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ASAPlus/1.0 (Acao Social Adventista)"},
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status != 200:
                    raise ViaCEPConnectionError(f"Serviço ViaCEP retornou status {response.status}.")

                raw_data = response.read().decode("utf-8")
                data = json.loads(raw_data)

        except urllib.error.HTTPError as exc:
            raise ViaCEPConnectionError(f"Erro HTTP ao consultar ViaCEP: {exc.code} {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise ViaCEPConnectionError(f"Erro de conexão com serviço ViaCEP: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ViaCEPConnectionError("Tempo limite excedido ao consultar o serviço ViaCEP.") from exc
        except json.JSONDecodeError as exc:
            raise ViaCEPConnectionError("Resposta inválida do serviço ViaCEP.") from exc

        if data.get("erro") is True or data.get("erro") == "true":
            raise CEPNotFoundError(f"O CEP '{cep}' não foi localizado na base do ViaCEP.")

        return AddressData(
            cep=data.get("cep", cleaned_cep),
            street=data.get("logradouro", ""),
            neighborhood=data.get("bairro", ""),
            city=data.get("localidade", ""),
            state=data.get("uf", ""),
            complement=data.get("complemento", ""),
        )
