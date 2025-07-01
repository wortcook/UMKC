terraform {
  required_providers {
    docker = {
      source = "kreuzwerker/docker"
      version = "~> 3.0.1"
    }
  }
}

resource "docker_image" "llm-stub" {
  name = "us-central1-docker.pkg.dev/thomasjones-llm-project-2025/llm-project/llm-stub:latest"
  build {
    context = "./llmstub"
    tag = ["llm-stub:latest"]
  }
  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset(path.module, "./llm-stub/src/**") : filesha1(f)]))
  }
  force_remove = true
  keep_locally = false
}

resource "null_resource" "tag_image" {
  depends_on = [docker_image.llm-stub]
  provisioner "local-exec" {
    command = "docker tag llm-stub ${docker_image.llm-stub.name}"
  }
}

resource "null_resource" "push_image" {
  depends_on = [null_resource.tag_image]
  provisioner "local-exec" {
    command = "docker push ${docker_image.llm-stub.name}"
  }
}

