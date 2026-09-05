# Astrolabe en AWS (eu-north-1) — patrón "bajo demanda"

Provisiona con Terraform:

1. **EC2 parada por defecto** (t3.xlarge) con EIP, SSM y user-data que instala Docker.
2. **Función Lambda "wake"** (`${project}-wake`, URL pública function URL) que:
   - `GET /` → enciende la VM y espera a que pase a `running`; **arma un schedule
     one-shot de EventBridge Scheduler** que la para en `auto_stop_seconds`
     (anti-olvido; se regenera en cada arranque).
   - `GET /?action=stop` → para la VM y cancela el schedule pendiente.
3. **S3 + CloudFront (OAC, PriceClass_100)** con el frontend estático: la web
   queda siempre visible aunque la VM esté parada.

## Uso

```sh
cp terraform.tfvars.example terraform.tfvars   # ajusta frontend_bucket (único global)
terraform init
terraform plan
terraform apply
```

Tras el apply:

```sh
curl "$(terraform output -raw wake_url)"            # enciende + auto-stop en 3 h
curl "$(terraform output -raw wake_url)?action=stop" # apaga manualmente
```

## Coste (orientativo, eu-north-1, on-demand)

| Componente | Coste |
|---|---|
| t3.xlarge apagada | €0 |
| t3.xlarge encendida | ~$0.168/h |
| Lambda wake | ~$0 (ociosa no cobra) |
| EIP con instancia parada | ~$3.6/mes (EIP gratis solo si la VM corre) |
| S3 + CloudFront (PriceClass_100) | céntimos/mes |
| CloudWatch Logs | 7 días retención, ~$0 si usas poco |

El anti-olvido garantiza que una VM olvidada encendida se apague sola en
`auto_stop_seconds`, protegiendo el saldo.

## Seguridad (lee esto)

- **`authorization_type = "NONE"`** en la function URL: cualquiera que conozca la
  URL puede encender/apagar tu instancia. Para un demo es aceptable (riesgo: que
  te la enciendan → coste). Más adelante protégela con CloudFront + una cabecera
  secreta o con un API Gateway con API key. El coste de riesgo es, como mucho,
  `auto_stop_seconds` de t3.
- El EC2 **no** abre SSH público (solo SSM, 443 saliente). Docker y los deploys
  entran por `aws ssm send-command`.

## Pendiente (siguientes pasos)

- ECR (repos `kgraph/backend`, `kgraph/frontend`) + despliegue vía
  SSM `SendCommand` activando `docker compose pull && up`.
- GitHub Actions con OIDC → rol IAM (push ECR + `scheduler` de LLM). 
- Dominio propio: Route 53 + certificado ACM + CloudFront con `viewer_certificate`
  custom y DNS del backend. Mientras tanto, el backend va por http://`backend_public_ip`.
- Estado remoto (bucket S3) cuando haya más de una persona tocando el tf.