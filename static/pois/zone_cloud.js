function cloud_init(width, height, zone_id) {

var svg = d3.select("[id=zone_cloud]")
	.append("svg")
    .attr("width", width)
    .attr("height", height);

var force = d3.layout.force()
    .gravity(.05)
    .distance(120) //(100)
    .charge(-100) //(-100)
.linkStrength(0.5) // (1.0)
.friction(0.1) // (0.9)
    .size([width, height]);

d3.json("/zonenet?zone_id="+zone_id+"&width="+width+"&height="+height, function(json) {
  force
      .nodes(json.nodes)
      .links(json.links)
      .start();

safety = 0;
while(force.alpha() > 0.01) {
    force.tick();
    if(safety++ > 5000) {
      break; // Avoids infinite looping in case this solution was a bad idea
    }
}

var link = svg.selectAll(".link")
    .data(json.links)
    .enter().append("line")
    .attr("class", "link");

var nodeEnter = svg.selectAll(".node")
    .data(json.nodes)     
    .enter()
    .append("a")
    .attr("xlink:xlink:href", function(d){ return '/pois/zone/' + d.id })
    .attr("class", "node")
    .append("g");

nodeEnter
    .append("rect")
    .attr("x", -30)
    .attr("y", -15)
    .attr("width", 60)
    .attr("height", 20);
nodeEnter
    .append("text")
    .attr("text-anchor", "middle")
    .attr("font-size", function(d) { return Math.max(12, d.importance*8) })
    .attr("fill", function(d) { return d.color })
    .text(function(d) { return d.name });

var node = nodeEnter
    .call(force.drag);

force.on("tick", function() {
    node.attr("cx", function(d) { return d.x = Math.min(Math.max(d.x, 40), width-40); })
        .attr("cy", function(d) { return d.y = Math.min(Math.max(d.y, 20), height-20); });
    link.attr("x1", function(d) { return d.source.x; })
        .attr("y1", function(d) { return d.source.y; })
        .attr("x2", function(d) { return d.target.x; })
        .attr("y2", function(d) { return d.target.y; });
    node.attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });
  });
});

}