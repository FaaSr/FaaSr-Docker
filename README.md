# Building FaaSr containers

This repo contains GitHub actions for pushing containers of two types: **base** and **platform specific**.  

---

### Base
- **rocker-base → DockerHub**  
  Builds an image from a Rocker base containing both R and Python, and pushes it to DockerHub.  
  *This base is preferred over r-base for R images.*

- **r-base → DockerHub**  
  Builds an image from a Debian Python base containing both R and Python to DockerHub.  
  *(deprecated — testing purposes only)*

- **py-base → DockerHub**  
  Builds an image from a Debian Python base containing just Python.  

---

### Platform Specific
- **github-actions → GHCR**  
  Builds a GitHub Action specific image from a FaaSr base container, and pushes it to GHCR.

- **openwhisk → DockerHub**  
  Builds an OpenWhisk specific image from a FaaSr base container, and pushes it to DockerHub.

- **aws-lambda → ECR**  
  Builds an AWS Lambda specific image from a FaaSr base container, and pushes it to AWS ECR.

- **GCP → DockerHub**  
  Builds a GCP specifc image from a FaaSr base container, and pushes it to DockerHub.

- **slurm → DockerHub**  
  Builds a slurm specifc image from a FaaSr base container, and pushes it to DockerHub.  

---

**Note:** The type of FaaSr base image the platform specific images build from will determine which type of functions they support.  

For example:  
- A GitHub Action image built from a `py-base` image will **not** be able to support R runtimes.  
- Although you can technically run both R and Python using the `rocker-base` and `r-base` images, it is recommended to use them only for **R functions**.  

---

# Setup

Before you can use this repo, you will have to make a fork of it on your GitHub account.  
For more info, see [here](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo).  

When you navigate to the **Actions** tab, GitHub may prompt you to enable GitHub actions — click **Agree**.  

---

In order to use any of the actions in this repo, you will need a **DockerHub account**.  
For AWS images, you will also need an **ECR repo**.  

To add these credentials to the repo:  
- Add `DOCKERHUB_TOKEN` and `DOCKERHUB_USERNAME` to your secrets by navigating to  
  **Settings → Secrets and variables → Actions → New repository secret**  

If using ECR, you will also need to add `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.  

---

# Usage

1. Navigate to the **Actions** tab and select the type of image you would like to build.  
2. Click **Run workflow**.  
3. You will be prompted for some inputs:  
   - For base images, the default base image will work.  
   - For platform specific images, you’ll need to provide a FaaSr base image (e.g., `faasr/base-r:latest`, `faasr/base-python:latest`, etc.).  
4. Run the action and your image will be pushed.  
   - By default, the version tagged to your image will match the FaaSr version you use.  

---

# ECR setup

You need to create a private **ECR repository** on AWS:

- Login to the AWS console.  
- Search **Elastic Container Registry** and go to the service.  
- On the left panel, click **Private Registry → Repositories**.  
- Create the repository by clicking **Create repository** (top right).  
- Create the image with the tag under the name of repository (e.g., `aws-lambda-tidyverse:new-image`).  
- Refer to the **View push commands** to create the image.  

---

You need to configure a private ECR repository to allow others to use your image:

- On the main panel, click the repository name (e.g., `aws-lambda-tidyverse`).  
- On the left panel, click **Permissions**.  
- Click **Edit policy JSON** (top right) and paste the JSON configuration below.  
  *Edit the region and id as needed (e.g., region: us-east-1, id: 797586564395).*  

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaECRImageRetrievalPolicy",
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": [
        "ecr:BatchGetImage",
        "ecr:DeleteRepositoryPolicy",
        "ecr:GetDownloadUrlForLayer",
        "ecr:GetRepositoryPolicy",
        "ecr:SetRepositoryPolicy"
      ],
      "Condition": {
        "StringLike": {
          "aws:sourceArn": "arn:aws:lambda:<<your aws region>>:<<your aws id>>:function:*"
        }
      }
    },
    {
      "Sid": "CrossAccountPermission",
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ]
    },
    {
      "Sid": "LambdaECRImageCrossAccountRetrievalPolicy",
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Condition": {
        "StringLike": {
          "aws:sourceARN": "*"
        }
      }
    }
  ]
}
```

---

**Notes**:  
- Ensure that the ECR repo you’ve created matches the **region** you plan to push images to.
