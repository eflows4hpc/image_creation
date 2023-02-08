#!/bin/bash

# request build

user=$1
passwd=$2
url=$3
action=$4

shift 4
echo "Response:"
if [ "$action" == "build" ]; then
   request=$1
   curl -k -L -X POST $url/image_creation/build \
      -H "Content-Type: application/json" \
      -d @$request --user "$user:$passwd"
elif [ "$action" == "status" ]; then
   id=$1
   curl -k -L -X GET $url/image_creation/build/$id --user "$user:$passwd"
elif [ "$action" == "download" ]; then
   image=$1
   wget --no-check-certificate --user $user --password $passwd $url/image_creation/images/download/$image
fi
echo ""
