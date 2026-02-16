# ASAplus 💙

> Sistema de Gestão e Acompanhamento para a Ação Solidária Adventista (ASA).

O **ASAplus** é uma solução open-source desenvolvida para modernizar e facilitar a administração dos departamentos da ASA nas igrejas locais. O objetivo é sair das planilhas de papel e ter um controle real sobre as famílias assistidas e a efetividade dos projetos missionários.

Construído com a filosofia de **"Monólito Modular"** para ser leve, rápido e fácil de implantar em qualquer computador da igreja ou servidor modesto.

## 🚀 Tecnologias (The TALL-D Stack)

Este projeto utiliza uma stack moderna focada em alta produtividade e renderização no servidor (Server-Side Rendering), evitando a complexidade desnecessária de SPAs para este contexto.

* **Backend:** [Python 3.14](https://www.python.org/) + [Django 6.0](https://www.djangoproject.com/)
* **Frontend Dinâmico:** [HTMX](https://htmx.org/) (para interatividade sem recarregar a página)
* **Estilização:** [Tailwind CSS](https://tailwindcss.com/)
* **Componentes:** [Django Cotton](https://django-cotton.com/) (Sintaxe moderna `<c-component>` para templates)
* **Interatividade Leve:** [Alpine.js](https://alpinejs.dev/) (para modais e estados simples de UI)
* **Banco de Dados:** SQLite3 (Simples para início/dev, facilmente migrável para PostgreSQL)

## 🎯 Funcionalidades Principais (Escopo)

O sistema é desenhado para atender o fluxo de trabalho do Diretor da ASA:

### 1. Gestão de Beneficiários (Triagem)

* Cadastro completo de famílias.
* **Ficha Socioeconômica Digital:** Renda familiar, situação de moradia, saúde e desemprego.
* Histórico de atendimentos (evita duplicidade e ajuda no rodízio de auxílio).

### 2. Controle de Projetos e Campanhas

* Gestão de campanhas sazonais: *Mutirão de Natal*, *Inverno Solidário*, *Volta às Aulas*.
* Gestão de projetos contínuos: *Cursos de Geração de Renda*, *Horta Comunitária*.
* Vinculação de famílias a projetos específicos.

### 3. Estoque e Doações (Futuro)

* Entrada de doações (Alimentos, Roupas, Móveis).
* Saída de kits/cestas básicas com baixa automática.

### 4. Relatórios Inteligentes

* Geração automática de dados para o **Relatório Trimestral** (integrado com os requisitos da Associação/Missão).
* Métricas de impacto: Quantas pessoas atendidas, quilos de alimento distribuídos.

## 📂 Estrutura do Projeto

O projeto segue uma estrutura de **Monólito Modular**. Iniciamos com um único app para desenvolvimento rápido, mantendo a organização para futura extração de módulos se necessário.

```text
ASAplus/
├── core/                  # Configurações do projeto (Settings, WSGI, ASGI)
├── app/                   # O Coração do sistema (Monólito inicial)
│   ├── models/            # Modelagem (Famílias, Projetos, Visitas)
│   ├── views/             # Lógica de negócio e endpoints HTMX
│   ├── static/            # Arquivos estaticos (imagens, icones, etc)
│   ├── assets/            # Arquivos CSS processados pelo Tailwind
│   ├── assets/            # Regras de negocio do projeto
│   ├── templates/
│   │   └── cotton/        # Componentes UI reutilizáveis (Cards, Buttons, Inputs)
│   └── ...
├── static/                # Arquivos estaticos (imagens, icones, etc)
├── assets/                # Arquivos CSS processados pelo Tailwind
├── db.sqlite3             # Banco de dados local
└── manage.py
```

## ⚡ Como Rodar o Projeto

### Pré-requisitos

* Python 3.14+
* Git
* Poetry 2+

### Passo a Passo

1. **Clone o repositório:**

```bash
git clone https://github.com/loboeremita/asaplus.git
cd asaplus
```

2. **Instale as dependências:**

```bash
poetry install
```

3. **Execute as migrações:**

```bash
python manage.py migrate
```

4. **Inicie o servidor de desenvolvimento:**

```bash
python manage.py runserver
```

Acesse `http://127.0.0.1:8000` no seu navegador.

## 🛠️ Desenvolvimento com Tailwind CSS

```bash
# Em um terminal separado, para observar mudanças no CSS:
python manage.py tailwind watch
```

## 🤝 Contribuição

Este é um projeto para auxiliar a missão. Sinta-se à vontade para abrir *Issues* com sugestões de melhorias ou *Pull Requests*.

**Padrão de Commit:**

* `feat`: Nova funcionalidade (ex: cadastro de voluntários)
* `fix`: Correção de bug
* `docs`: Alteração em documentação
* `style`: Ajustes de formatação (Tailwind, Cotton)

---

**"Porque tive fome, e destes-me de comer; tive sede, e destes-me de beber..." - Mateus 25:35**
