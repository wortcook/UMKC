provider "google" {
  project = var.project
  region  = "us-central1"
  zone    = "us-central1-c"
  credentials = file("thomasjones-llm-project-2025-7725b32a4ec0.json")
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

resource "google_compute_firewall" "allow_ssh_ingress" {
  name        = "allow-ssh-ingress"
  network     = google_compute_network.llm-vpc.name # Reference the custom VPC network
  priority    = 1000 # Lower number means higher priority
  direction   = "INGRESS"
  source_ranges = ["0.0.0.0/0"] # Allow SSH from any source
  allow {
    protocol = "tcp"
    ports    = ["22"] # Allow SSH on port 22
  }
}

resource "google_compute_firewall" "allow_http_https" {
  name        = "allow-ssh-ingress"
  network     = google_compute_network.llm-vpc.name # Reference the custom VPC network
  priority    = 1000 # Lower number means higher priority
  direction   = "INGRESS"
  source_ranges = ["0.0.0.0/0"] # Allow SSH from any source
  allow {
    protocol = "http"
    ports    = ["80"] # Allow SSH on port 22
  }
  allow {
    protocol = "https"
    ports    = ["443"] # Allow SSH on port 22
  }
}

#REMAINING SUBNETS TBD
