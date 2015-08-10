#!/usr/bin/env python
import cli.log

import boto


@cli.log.LoggingApp
def gen_s3_link(app):
    c = boto.connect_s3()
    print c.generate_url(app.params.expire, app.params.method, app.params.bucket, app.params.name,
                   force_http=app.params.schema=='HTTP')

gen_s3_link.add_param("-b", "--bucket", help="The bucket name", type=str, required=True)
gen_s3_link.add_param("-n", '--name', help="The file name/path", type=str, required=True)
gen_s3_link.add_param("-m", '--method', help="The http method", type=str, default="PUT")
gen_s3_link.add_param("-S", '--schema', help="The schema, http or https", type=str, default="HTTP")
gen_s3_link.add_param("-e", '--expire', help="The link expiry seconds", type=int, default=3999999)

if __name__ == "__main__":
    gen_s3_link.run()
