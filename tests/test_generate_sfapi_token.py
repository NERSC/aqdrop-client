import pytest

from aqdrop import generate_sfapi_token


def test_generate_token_reads_client_id_and_private_key_files(tmp_path, monkeypatch, capsys):
    client_id_file = tmp_path / "client-id"
    client_id_file.write_text("client-123\n", encoding="utf-8")
    private_key_file = tmp_path / "private-key.pem"
    private_key_file.write_bytes(b"private-key")
    captured = {}

    def fake_fetch(client_id, private_key_path, token_url=None):
        captured.update(
            client_id=client_id,
            private_key_path=private_key_path,
            token_url=token_url,
        )
        return "generated-token"

    monkeypatch.setattr(generate_sfapi_token.creds, "fetch_sfapi_token", fake_fetch)

    generate_sfapi_token.main(
        [
            "--client-id-file",
            str(client_id_file),
            "--private-key-file",
            str(private_key_file),
            "--token-url",
            "https://oidc.example/token",
        ]
    )

    assert captured == {
        "client_id": "client-123",
        "private_key_path": str(private_key_file),
        "token_url": "https://oidc.example/token",
    }
    assert capsys.readouterr().out == "generated-token\n"


@pytest.mark.parametrize("client_id", ["", "client one", "client-1\nclient-2"])
def test_generate_token_rejects_invalid_client_id_file(tmp_path, client_id):
    client_id_file = tmp_path / "client-id"
    client_id_file.write_text(client_id, encoding="utf-8")
    private_key_file = tmp_path / "private-key.pem"
    private_key_file.write_bytes(b"private-key")

    with pytest.raises(SystemExit) as exc_info:
        generate_sfapi_token.main(
            [
                "--client-id-file",
                str(client_id_file),
                "--private-key-file",
                str(private_key_file),
            ]
        )

    assert exc_info.value.code == 2
