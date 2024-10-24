export SUPERSET_URL="http://localhost:8088"

# Authenticate and get an access token
# The response will include an access token. Use this token in the following requests.
export access_token=$(curl -s -X POST \
  $SUPERSET_URL/api/v1/security/login \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "admin",
    "password": "admin",
    "provider": "db"
  }' | jq '.access_token' | tr -d '"')

# Import database connection
echo curl -X POST \
  "${SUPERSET_URL}/api/v1/database/import/" \
  -H "Content-Type: multipart/form-data" \
  -H "Authorization: Bearer '${access_token}'" \
  -F "formData=./database.yaml"

# Import datasets
curl -X POST \
  $SUPERSET_URL/api/v1/dataset/import/ \
  -H 'Content-Type: multipart/form-data' \
  -H 'Authorization: Bearer $access_token' \
  -F 'formData=./datasets.yaml'

# Import charts
curl -X POST \
  $SUPERSET_URL/api/v1/chart/import/ \
  -H 'Content-Type: multipart/form-data' \
  -H 'Authorization: Bearer $access_token' \
  -F 'formData=./charts.yaml'

# Import dashboard
curl -X POST \
  $SUPERSET_URL/api/v1/dashboard/import/ \
  -H 'Content-Type: multipart/form-data' \
  -H 'Authorization: Bearer $access_token' \
  -F 'formData=./dashboard.yaml'