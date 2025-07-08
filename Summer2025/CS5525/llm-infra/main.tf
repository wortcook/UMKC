terraform {
  required_providers {
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
  }
}

provider "google" {
  project = var.project
  region  = "us-central1"
  zone    = "us-central1-c"
  #  credentials = file("thomasjones-llm-project-2025-7725b32a4ec0.json")
}

data "google_project" "project" {
}

resource "google_project_service" "project_apis" {
  project  = var.project
  for_each = toset([
    "iam.googleapis.com",
    "run.googleapis.com",
    "compute.googleapis.com",
    "storage.googleapis.com",
    "artifactregistry.googleapis.com",
  ])
  service                    = each.key
  disable_on_destroy         = true
}

resource "google_compute_network" "llm-vpc" {
  name                    = "llm-vpc"
  auto_create_subnetworks = false
  mtu                     = 1460

  # Ensure the Compute API is enabled before creating the network.
  depends_on = [google_project_service.project_apis]
}

resource "google_compute_subnetwork" "llm-vpc-filter-subnet" {
  name          = "llm-vpc-filter-subnet"
  ip_cidr_range = "10.0.1.0/24"
  region        = "us-central1"
  private_ip_google_access = true
  network       = google_compute_network.llm-vpc.id

  depends_on = [null_resource.destroy_delay]
}

resource "null_resource" "destroy_delay" {
  # This resource introduces a delay during the destroy operation. It does not
  # depend on any other resource, which prevents dependency cycles. During a
  # 'destroy' operation, any resource that depends on this one will have to
  # wait for the provisioner's command to complete before it is destroyed.
  provisioner "local-exec" {
    when    = destroy
    command = "sleep 30"
  }
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

  depends_on = [null_resource.destroy_delay]
}

###############
# STORAGE
###############
resource "google_storage_bucket" "model-store" {
  name     = "model-store-${var.project}"
  location = "us-central1"

  # When deleting the bucket, this will also delete all objects in it.
  force_destroy = true

  uniform_bucket_level_access = true

  # Ensure the Storage API is enabled before creating the bucket.
  depends_on = [google_project_service.project_apis]
}

module "model-downloader-build" {
  source     = "./model-downloader"
  project_id = var.project

  # Ensure Artifact Registry API is enabled before building/pushing images.
  depends_on = [google_project_service.project_apis]
}

resource "google_service_account" "model_downloader_sa" {
  account_id   = "model-downloader-sa"
  display_name = "Model Downloader Service Account"
  project      = var.project

  # Ensure the IAM API is enabled before creating the service account.
  depends_on = [google_project_service.project_apis]
}

resource "google_storage_bucket_iam_member" "model_downloader_gcs_writer" {
  bucket = google_storage_bucket.model-store.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.model_downloader_sa.email}"
}

resource "null_resource" "model-download" {
  triggers = {
    # Re-run the job if the job definition, model name, or container image changes.
    job_id     = google_cloud_run_v2_job.model_downloader_job.id
    model_name = var.secondary_model_name
    image_id   = module.model-downloader-build.image_id
  }

  provisioner "local-exec" {
    # This command executes the Cloud Run Job.
    command = "gcloud run jobs execute ${google_cloud_run_v2_job.model_downloader_job.name} --region ${google_cloud_run_v2_job.model_downloader_job.location} --wait --project ${var.project}"
  }

  depends_on = [google_cloud_run_v2_job.model_downloader_job]
}

###############
# SERVICE ACCOUNTS & PERMISSIONS
###############

resource "google_service_account" "llm_stub_sa" {
  account_id   = "llm-stub-sa"
  display_name = "LLM Stub Service Account"
  project      = var.project
  depends_on   = [google_project_service.project_apis]
}

resource "google_service_account" "sfilter_sa" {
  account_id   = "sfilter-sa"
  display_name = "SFilter Service Account"
  project      = var.project
  depends_on   = [google_project_service.project_apis]
}

# Grant the sfilter service account read access to the model bucket.
# This ensures the process within the container (running as this SA)
# can read files from the GCS FUSE volume mount.
resource "google_storage_bucket_iam_member" "sfilter_gcs_reader" {
  bucket = google_storage_bucket.model-store.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.sfilter_sa.email}"
}

# Grant the Cloud Run Service Agent permission to mount GCS volumes for services.
# This is required for the GCS volume mount feature to work, as Cloud Run
# infrastructure accesses the bucket on the service's behalf.
resource "google_storage_bucket_iam_member" "run_service_agent_gcs_mount_access" {
  bucket = google_storage_bucket.model-store.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:service-${data.google_project.project.number}@serverless-robot-prod.iam.gserviceaccount.com"
  depends_on = [google_project_service.project_apis] # Ensures the Run API is enabled, which creates the service agent.
}

resource "google_service_account" "bfilter_sa" {
  account_id   = "bfilter-sa"
  display_name = "BFilter Service Account"
  project      = var.project
  depends_on   = [google_project_service.project_apis]
}

# Grant bfilter service account permission to invoke llm-stub service.
resource "google_cloud_run_v2_service_iam_member" "bfilter_invokes_llmstub" {
  project  = google_cloud_run_v2_service.llm-stub-service.project
  location = google_cloud_run_v2_service.llm-stub-service.location
  name     = google_cloud_run_v2_service.llm-stub-service.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.bfilter_sa.email}"
}

# Grant bfilter service account permission to invoke sfilter service.
resource "google_cloud_run_v2_service_iam_member" "bfilter_invokes_sfilter" {
  project  = google_cloud_run_v2_service.sfilter-service.project
  location = google_cloud_run_v2_service.sfilter-service.location
  name     = google_cloud_run_v2_service.sfilter-service.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.bfilter_sa.email}"
}

###############
# SERVICE WORKERS
###############
module "llm-stub-build" {
  source     = "./llmstub"
  project_id = var.project

  # Ensure Artifact Registry API is enabled before building/pushing images.
  depends_on = [google_project_service.project_apis]
}

module "sfilter-build" {
  source       = "./sfilter"

  # Ensure Artifact Registry API is enabled before building/pushing images.
  depends_on = [google_project_service.project_apis]
}

module "bfilter-build" {
  source       = "./bfilter"

  # Ensure Artifact Registry API is enabled before building/pushing images.
  depends_on = [google_project_service.project_apis]
}

resource "google_cloud_run_v2_service" "llm-stub-service" {
  name     = "llm-stub-service"
  location = "us-central1"
  deletion_protection = false

  ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"
 
  template {
    service_account = google_service_account.llm_stub_sa.email
    containers {
      image = module.llm-stub-build.image_name
      ports {
        container_port = var.llm_stub_port
      }
    }
  }

  # Ensure the Run API is enabled and the image is built.
  depends_on = [module.llm-stub-build, google_project_service.project_apis, google_service_account.llm_stub_sa]
}

resource "google_cloud_run_v2_service" "sfilter-service" {
  name     = "sfilter-service"
  location = "us-central1"
  deletion_protection = false

  ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.sfilter_sa.email
    containers {
      image = module.sfilter-build.image_name
      ports {
        container_port = var.sfilter_port
      }
      env {
        name  = "SECONDARY_MODEL"
        value = var.secondary_model_location
      }

      volume_mounts {
          name       = "model-store-volume"
          mount_path = "/storage/models"
      }

      resources {
        limits = {
          memory = "32Gi"
          cpu    = "8"
        }
      }
    }

    volumes {
      name = "model-store-volume"
      gcs {
        bucket    = google_storage_bucket.model-store.name
        read_only = true # The service only needs to read the model.
      }
    }
  }
  depends_on = [module.sfilter-build, google_project_service.project_apis, google_cloud_run_v2_job.model_downloader_job, google_storage_bucket_iam_member.run_service_agent_gcs_mount_access]
}

resource "google_cloud_run_v2_service" "bfilter-service" {
  name     = "bfilter-service"
  location = "us-central1"
  deletion_protection = false

  template {
    service_account = google_service_account.bfilter_sa.email
    vpc_access{
      network_interfaces {
        network = google_compute_network.llm-vpc.id
        subnetwork = google_compute_subnetwork.llm-vpc-filter-subnet.id
      }
      egress = "ALL_TRAFFIC"
    }

    containers {
      image = module.bfilter-build.image_name
      ports {
        container_port = var.bfilter_port
      }
      env {
        name  = "LLMSTUB_URL"
        value = google_cloud_run_v2_service.llm-stub-service.uri
      }
      env{
        name = "SFILTER_URL"
        value = google_cloud_run_v2_service.sfilter-service.uri
      }
    }
  }

  depends_on = [module.bfilter-build, google_cloud_run_v2_service.llm-stub-service, google_cloud_run_v2_service.sfilter-service, google_project_service.project_apis, google_service_account.bfilter_sa]
}

# WARNING: This makes the bfilter-service publicly accessible to anyone on the internet.
# Only use this if the service is explicitly designed for unauthenticated public access.
resource "google_cloud_run_v2_service_iam_member" "bfilter_public_invoker" {
  project  = google_cloud_run_v2_service.bfilter-service.project
  location = google_cloud_run_v2_service.bfilter-service.location
  name     = google_cloud_run_v2_service.bfilter-service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_job" "model_downloader_job" {
  name     = "model-downloader-job"
  location = "us-central1"
  project  = var.project
  deletion_protection = false

  template {
    template {
      service_account = google_service_account.model_downloader_sa.email
      containers {
        image = module.model-downloader-build.image_name
        env {
          name  = "HF_MODEL_NAME"
          value = var.secondary_model_name
        }
        env {
          name  = "GCS_BUCKET_NAME"
          value = google_storage_bucket.model-store.name
        }
        resources {
          limits = {
            memory = "4Gi"
            cpu    = "2"
          }
        }
      }
      timeout = "3600s" # 1 hour
    }
  }
  depends_on = [module.model-downloader-build, google_storage_bucket_iam_member.model_downloader_gcs_writer]
}