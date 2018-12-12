@Library('pipeline-library') _

pipeline {
  agent { label 'docker' }
  stages {
    stage('Build') {
      steps {
        sh "docker build -t openstax/cnx-db:dev ."
      }
    }
    stage('Test Container Build') {
      steps {
        sh "docker run --name ${meta.getContainerName()} -d openstax/cnx-db:dev"
        // Give the server time to startup
        sh "sleep 20s"
        // If this command is successful, then the container is accepting connections
        sh "docker run --rm --link ${meta.getContainerName()}:db openstax/cnx-db:dev psql -h db -U postgres -c \"\\l\""
        // ^^^ If this is failing, it usually means the base container is out-of-date.
      }
      post {
        always {
          sh "docker rm -f ${meta.getContainerName()}"
        }
      }
    }
    stage('Publish Dev Container') {
      when {
        anyOf {
          branch 'master'
          buildingTag()
        }
      }
      steps {
        // 'docker-registry' is defined in Jenkins under credentials
        withDockerRegistry([credentialsId: 'docker-registry', url: '']) {
          sh "docker push openstax/cnx-db:dev"
        }
      }
    }
    stage('Publish Release') {
      when { buildingTag() }
      environment {
        TWINE_CREDS = credentials('pypi-openstax-creds')
        TWINE_USERNAME = "${TWINE_CREDS_USR}"
        TWINE_PASSWORD = "${TWINE_CREDS_PSW}"
        release = meta.version()
      }
      steps {
        withDockerRegistry([credentialsId: 'docker-registry', url: '']) {
          sh "docker tag openstax/cnx-db:dev openstax/cnx-db:${release}"
          sh "docker tag openstax/cnx-db:dev openstax/cnx-db:latest"
          sh "docker push openstax/cnx-db:${release}"
          sh "docker push openstax/cnx-db:latest"
        }
        // Note, '.git' is a volume, because versioneer needs it to resolve the python distribution's version. 
        sh "docker run --rm -e TWINE_USERNAME -e TWINE_PASSWORD -v ${WORKSPACE}/.git:/src/.git:ro openstax/cnx-db:latest /bin/bash -c \"pip install -q twine && python setup.py bdist_wheel --universal && twine upload dist/*\""
      }
    }
  }
}
