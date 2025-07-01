provider "google" {
  project = var.project
  region  = "us-central1"
  zone    = "us-central1-c"
  #  credentials = file("thomasjones-llm-project-2025-7725b32a4ec0.json")
}

resource "google_compute_network" "llm-vpc" {
  name                    = "llm-vpc"
  auto_create_subnetworks = false
  mtu                     = 1460
}

resource "google_compute_subnetwork" "default" {
  name          = "llm-vpc-subnet"
  ip_cidr_range = "10.0.1.0/24"
  region        = "us-central1"
  network       = google_compute_network.llm-vpc.id
}

resource "google_compute_firewall" "default" {
  name        = "allow-ssh-http-https-ingress"
  network     = google_compute_network.llm-vpc.name # Reference the custom VPC network
  priority    = 1000 # Lower number means higher priority
  direction   = "INGRESS"
  source_ranges = ["0.0.0.0/0"] # Allow SSH from any source
  allow {
    protocol = "tcp"
    ports    = ["22","80","443"] # Allow SSH on port 22
  }
}

module "llm-stub-build" {
  source = "./llmstub" # Path to your module directory
}

module "bfilter-build" {
  source = "./bfilter" # Path to your module directory
}

resource "google_cloud_run_v2_service" "bfilter-service" {
  name = "bfilter-service"
  location = "us-central1"
  deletion_protection = false
  template {
      containers {
        image = "us-central1-docker.pkg.dev/thomasjones-llm-project-2025/llm-project/bfilter:latest"
        ports {
          container_port = 8082
        }
      }
  }
  depends_on = [ module.bfilter-build ]
}


resource "google_cloud_run_v2_service" "llm-stub-service" {
  name = "llm-stub-service"
  location = "us-central1"
  deletion_protection = false
  template {
      containers {
        image = "us-central1-docker.pkg.dev/thomasjones-llm-project-2025/llm-project/llm-stub:latest"
        ports {
          container_port = 8081
        }
      }
  }
  depends_on = [ module.llm-stub-build ]
}

data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "noauth" {
  location    = google_cloud_run_v2_service.llm-stub-service.location
  project     = google_cloud_run_v2_service.llm-stub-service.project
  service     = google_cloud_run_v2_service.llm-stub-service.name

  policy_data = data.google_iam_policy.noauth.policy_data
}

#REMAINING SUBNETS TBD
