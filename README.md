AWS CodeDeploy Multiplexer
==========================
This code base allows customers with multiple applications that live in separate Github
repositories but run on the same server easily deployable as a single Deployment Group.

For information on why multiple deployment groups can be painful see the [AWS Docs](http://docs.aws.amazon.com/codedeploy/latest/userguide/troubleshooting-auto-scaling.html#troubleshooting-multiple-depgroups).

The command named `multiplexer` handles the heavy lifting for this solution which
includes downloading the necessary packages from Github and then merging the
repositories into a single artifact. Each application repository should have it's
own Appspec files and scripts, these will be merged into a single appspec file with
the paths rewritten to ensure they still point to the correct files.

For Example:

App1
```
scripts/
  install.sh
src/
  appfile.php
appspec.yml
```


App2
```
scripts/
  install.sh
src/
  appfile.php
appspec.yml
```

The above two applications will be merged into a new artifact that looks like the
following.
```
app1/
  scripts/
    install.sh
  src/
    appfile.php
app2/
  scripts/
    install.sh
  src/appfile.php
appspec.yml
```

Deployment
----------
To deploy this solution you need a bucket to keep your deployment package and
configuration file for the solution. The nice thing is that this is a completely
self contained solution and only requires a few steps. To create the standard
build package you need the GNU Make and the zip commands.

#### Build Package
Running the following should result in a file named `build.zip` this file is
your "build" package.
```
make package
```

Once your build package is created, you need to add it to an S3 bucket of your
choosing. It is common to use the same bucket for both your build package and
your config file however it is not required.

#### CloudFormation
To deploy the infrastructure for this solution, use the CloudFormation.yaml
template to create a new stack.

- `ArtifactBucket` - S3 Bucket that the resulting artifacts will be stored in.
- `BuildSourceBucket` - S3 Bucket that houses your [build package](#build-package).
- `BuildSourceSpec` - If you customized your own build package and use a file other than
  buildspec.yml ensure to update this property.
- `BuildSourceName` - The name of the build package, use the default unless you renamed
  the build package.
- `ConfigBucket` - The S3 Bucket that houses your configuration file.
- `ConfigName` - The S3 Key for your configuration file.
- `GithubToken` - A Github token that has access to all applications that will be packaged
  using this solution.


#### Github
To configure your Github webhook, on each repository use the outputs from the CloudFormation
stack.

- `Payload URL` - Use the WebhookUrl provided by the CloudFormation stack.
- `Content Type` - Make sure "application/json" is selected
- `Secret` - Use the Secret provided by the CloudFormation stack.
