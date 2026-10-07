# Sharing and Teams

Sharing is available on the **account portal**. Anyone who can open a dataset can copy a dashboard link from **Share**. Only the dataset owner can add or remove users and teams. The public portal can view datasets that are already marked public.

## Share with a Person

1. Select a dataset you own
2. In dataset details, click **Share**
3. Under **Share with Users**, enter one or more email addresses
4. Click **Share with Users**

That person sees the dataset under **Shared with Me** after they sign in.

## Share with a Team

1. Create a team from the toolbar **Team** button (name plus member emails)
2. Open **Share** on a dataset you own
3. Under **Share with Teams**, choose the team
4. Click **Share with Team**

All current team members see it under **Team Datasets**. You can also assign a team when you upload or when you connect S3 data.

## Dashboard Link

**Share** and **Copy Dashboard Link** copy a URL that opens the dataset in a dashboard. Use it to send someone straight to the view. Recipients still need permission (owner, share, team, or public) for private data. If you do not own the dataset, Share still copies that link; it does not let you add users or teams.

## Public Visibility

When you upload or edit a dataset you can:

- Mark it **public** so it appears on `https://scientistcloud.com/portal/public/`
- Set download permission: **only owner**, **only team**, or **public**

Public browse is not the same as public download. A dataset can be viewable in a dashboard without being downloadable.

## API

Team and share endpoints (owner email required):

```bash
# Create a team
curl -X POST "https://scientistcloud.com/api/v1/teams?owner_email=you@example.com" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"team_name":"Lab Collaborators","emails":["user@example.com"]}'

# Share with a user
curl -X POST "https://scientistcloud.com/api/v1/share/user?owner_email=you@example.com" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dataset_uuid":"DATASET-UUID","user_email":"user@example.com"}'

# Share with a team
curl -X POST "https://scientistcloud.com/api/v1/share/team?owner_email=you@example.com" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dataset_uuid":"DATASET-UUID","team_name":"Lab Collaborators"}'
```

## Related

- [Folders](?page=folders) (shared and team datasets stay grouped by folder)
- [Dashboards](?page=dashboards)
- [Datasets API](?page=api-datasets)
