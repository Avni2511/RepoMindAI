from django.db import models

class Repository(models.Model):
    name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255, unique=True)
    repo_url = models.URLField(max_length=500)
    default_branch = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name


class CodeChunk(models.Model):
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    file_path = models.CharField(max_length=1000)
    start_line = models.PositiveIntegerField()
    end_line = models.PositiveIntegerField()
    content = models.TextField()
    embedding = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["repository", "file_path"]),
        ]

    def __str__(self):
        return f"{self.repository.full_name}:{self.file_path}:{self.start_line}"
